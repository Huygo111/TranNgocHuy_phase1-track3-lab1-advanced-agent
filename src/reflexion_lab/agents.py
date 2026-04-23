from __future__ import annotations
import json
import time
from dataclasses import dataclass, field
from typing import Literal

from .mock_runtime import call_actor, call_evaluator, call_reflector
from .prompts import ACTOR_SYSTEM, EVALUATOR_SYSTEM, REFLECTOR_SYSTEM
from .schemas import AttemptTrace, JudgeResult, QAExample, ReflectionEntry, RunRecord


def _build_actor_prompt(example: QAExample, reflection_memory: list[str]) -> str:
    context_text = "\n".join(
        f"[{chunk.title}]: {chunk.text}" for chunk in example.context
    )
    prompt = f"{ACTOR_SYSTEM}\n\nContext:\n{context_text}\n\nQuestion: {example.question}"
    if reflection_memory:
        notes = "\n".join(f"- {r}" for r in reflection_memory)
        prompt += f"\n\nReflection notes from previous failed attempts:\n{notes}"
    return prompt


def _build_evaluator_prompt(example: QAExample, predicted: str) -> str:
    return (
        f"{EVALUATOR_SYSTEM}\n\n"
        f"Question: {example.question}\n"
        f"Gold answer: {example.gold_answer}\n"
        f"Predicted answer: {predicted}"
    )


def _build_reflector_prompt(example: QAExample, predicted: str, reason: str) -> str:
    return (
        f"{REFLECTOR_SYSTEM}\n\n"
        f"Question: {example.question}\n"
        f"Gold answer: {example.gold_answer}\n"
        f"Wrong predicted answer: {predicted}\n"
        f"Evaluator reason: {reason}"
    )


def _parse_judge(raw: str) -> JudgeResult:
    """Parse JSON from evaluator, fallback gracefully."""
    try:
        # Ollama sometimes wraps JSON in markdown code fences
        text = raw.strip()
        if "```" in text:
            text = text.split("```")[1].strip()
            if text.startswith("json"):
                text = text[4:].strip()
        data = json.loads(text)
        return JudgeResult(
            score=int(data.get("score", 0)),
            reason=str(data.get("reason", "")),
        )
    except Exception:
        # fallback: check if response contains a clear yes/correct signal
        lower = raw.lower()
        score = 1 if ('"score": 1' in lower or "correct" in lower) else 0
        return JudgeResult(score=score, reason=raw[:200])


def _parse_reflection(raw: str, attempt_id: int) -> ReflectionEntry:
    """Parse JSON from reflector, fallback gracefully."""
    try:
        text = raw.strip()
        if "```" in text:
            text = text.split("```")[1].strip()
            if text.startswith("json"):
                text = text[4:].strip()
        data = json.loads(text)
        return ReflectionEntry(
            attempt_id=attempt_id,
            lesson=str(data.get("lesson", raw[:150])),
            strategy=str(data.get("strategy", "")),
        )
    except Exception:
        return ReflectionEntry(attempt_id=attempt_id, lesson=raw[:150], strategy="")


@dataclass
class BaseAgent:
    agent_type: Literal["react", "reflexion"]
    max_attempts: int = 1

    def run(self, example: QAExample) -> RunRecord:
        reflection_memory: list[str] = []
        reflections: list[ReflectionEntry] = []
        traces: list[AttemptTrace] = []
        final_answer = ""
        final_score = 0

        for attempt_id in range(1, self.max_attempts + 1):
            # ── Actor ──────────────────────────────────────────────────────
            actor_prompt = _build_actor_prompt(example, reflection_memory)
            t0 = time.time()
            actor_raw, actor_tokens = call_actor(actor_prompt)
            actor_latency = int((time.time() - t0) * 1000)

            # Extract answer from "Answer: ..." line, or take last line
            answer = actor_raw.strip()
            for line in actor_raw.splitlines():
                if line.lower().startswith("answer:"):
                    answer = line.split(":", 1)[1].strip()
                    break

            # ── Evaluator ──────────────────────────────────────────────────
            eval_prompt = _build_evaluator_prompt(example, answer)
            t1 = time.time()
            eval_raw, eval_tokens = call_evaluator(eval_prompt)
            eval_latency = int((time.time() - t1) * 1000)

            judge = _parse_judge(eval_raw)

            # Accumulate real token counts and latency
            token_estimate = actor_tokens + eval_tokens
            latency_ms = actor_latency + eval_latency

            trace = AttemptTrace(
                attempt_id=attempt_id,
                answer=answer,
                score=judge.score,
                reason=judge.reason,
                token_estimate=token_estimate,
                latency_ms=latency_ms,
            )
            final_answer = answer
            final_score = judge.score
            traces.append(trace)

            if judge.score == 1:
                break

            # ── Reflector (Reflexion only, not on last attempt) ────────────
            if self.agent_type == "reflexion" and attempt_id < self.max_attempts:
                refl_prompt = _build_reflector_prompt(example, answer, judge.reason)
                t2 = time.time()
                refl_raw, refl_tokens = call_reflector(refl_prompt)
                refl_latency = int((time.time() - t2) * 1000)

                entry = _parse_reflection(refl_raw, attempt_id)
                reflections.append(entry)

                # Update the last trace with reflection + extra tokens/latency
                traces[-1] = AttemptTrace(
                    attempt_id=attempt_id,
                    answer=answer,
                    score=judge.score,
                    reason=judge.reason,
                    reflection=entry,
                    token_estimate=token_estimate + refl_tokens,
                    latency_ms=latency_ms + refl_latency,
                )

                # Build memory string for next Actor call
                memory_line = f"Attempt {attempt_id}: {entry.lesson} → {entry.strategy}"
                reflection_memory.append(memory_line)

        total_tokens = sum(t.token_estimate for t in traces)
        total_latency = sum(t.latency_ms for t in traces)
        failure_mode = (
            "none"
            if final_score == 1
            else _infer_failure_mode(example, final_answer, traces)
        )

        return RunRecord(
            qid=example.qid,
            question=example.question,
            gold_answer=example.gold_answer,
            agent_type=self.agent_type,
            predicted_answer=final_answer,
            is_correct=bool(final_score),
            attempts=len(traces),
            token_estimate=total_tokens,
            latency_ms=total_latency,
            failure_mode=failure_mode,
            reflections=reflections,
            traces=traces,
        )


def _infer_failure_mode(
    example: QAExample, predicted: str, traces: list[AttemptTrace]
) -> str:
    """Heuristic failure mode classification."""
    gold = example.gold_answer.lower()
    pred = predicted.lower()

    if len(traces) >= 2 and traces[-1].answer == traces[-2].answer:
        return "looping"

    # Check if agent kept repeating the same wrong answer across attempts
    if len(traces) >= 3:
        answers = [t.answer.lower() for t in traces]
        if len(set(answers)) == 1:
            return "reflection_overfit"

    # If gold is multi-word and prediction shares some words but not all
    gold_words = set(gold.split())
    pred_words = set(pred.split())
    if gold_words & pred_words and gold_words != pred_words:
        return "incomplete_multi_hop"

    # If the prediction is factually coherent but about a different entity
    if len(pred) > 0 and pred not in gold and gold not in pred:
        return "entity_drift"

    return "wrong_final_answer"


class ReActAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(agent_type="react", max_attempts=1)


class ReflexionAgent(BaseAgent):
    def __init__(self, max_attempts: int = 3) -> None:
        super().__init__(agent_type="reflexion", max_attempts=max_attempts)

