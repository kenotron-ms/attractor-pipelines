Advance the candidate toward the externally verified predicate. Read candidate.txt, run_state/current_feedback.json, and run_state/attempt_state.json before acting. The feedback file is durable output derived from the external verifier's observed failure. The engine also injects the bounded verifier channel here:
Iteration 1 critique: FEEDBACK: Set status=valid and acknowledge this verifier feedback with feedback_ack=EXTERNAL_VERIFIER_REQUIRES_VALID_STATUS.
CANDIDATE_VERIFY:FAIL

Modify ONLY candidate.txt. Do not edit scripts, DOT, run_state, artifacts, or evidence. Overwrite candidate.txt with exactly these two UTF-8 lines, including the final newline:
status=valid
feedback_ack=EXTERNAL_VERIFIER_REQUIRES_VALID_STATUS

Use a real file-writing tool, then reread candidate.txt. Do not run or modify the verifier and do not claim PASS; only the external verifier and later parent verifier may decide success.