# Task 1 independent review

Spec compliance: FAIL. Task quality: Needs fixes.

Important, plan-mandated conflict: calibration/capture_demo_pose.py:59–60 sets urllib timeout1.5 then json.load(response), which consumes complete response.read(). Inactivity timeout is not an aggregate request/body deadline; slowly delivering bytes can exceed the promised7.5-second request-phase bound. Exact plan implementation makes this same assumption. Slow fake responses assume total1.49 seconds, not trickled longer responses.

Minor: host/monotonic clocks are advanced together in new tests; independently varied clocks should protect the requirement that both must span5 seconds.

Confirmed: five-argument compatibility and optional observer before validation; both clock-span checks;6-second request admission, bounded sleeps,30-sample generic floor; unchanged sample keys. Coherent fake host clocks. No Critical issue.

Cannot verify from task diff: existing builder40-floor, CLI exclusive creation and all prohibited files/services. Controller must resolve separately.

Reviewer examined installed json.load and HTTPResponse.read for this concrete risk, made no changes and reran no tests. User asked via asynchronous question to choose true aggregate timeout vs explicitly weakening timing claim; waiting for answer. Task not complete, no Task2 implementation/profile deployment yet.

