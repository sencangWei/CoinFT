# Acquisition auto-recovery design progress

Date: 2026-09-28. User approved automatic recovery, detailed design, written spec and split-task execution with independent review. Task1 worker is implementing the approved reader/API/tests; controller owns evidence, review and handoff.

## Current deployment state (supersedes historical blocked entries below)

- [x] User closed all three old instances; prelaunch CoinFT-process/listener counts both zero.
- [x] On the user's explicit request to handle startup, one ordinary authorized hidden Start-Process succeeded: PID18408, COM6, existing server8765, no-browser. No denial bypass or assistant process termination.
- [x] Subsequent point checks: one process/listener, new recovery schema, live/tare100,12 raw channels, frames28643->59607->71214, rate200.0-200.1Hz, invalid/saturated/resync0; pageGET200; reviewed backend hash unchanged. Evidence stream-recovery-deployment-single-service-20260928.json.
- [ ] Ten-second concurrent API/COM8 capture SKIPPED: composite command rejected before execution by CreateProcess policy; no COM8 opened and no alternate-method retry. Separate normal point checks are not continuous-window acceptance.
- [ ] Initial visible-page demo-zero/animation not inspected or performed; real same-process automatic stall/recovery acceptance remains pending (attempts0/successes0). Do not restart again solely to verify or claim physical recoveryPASS from healthy startup.

## Ordered design checklist

- [x] Explore context: PROJECT_LOG, complete serial reader/consumer, existing diagnostics/core tests and qualitative-page recovery handling. No Git metadata in this project; do not initialize a repository or claim a commit.
- [x] Visual companion: not applicable. No layout or animation change proposed; this is serial acquisition behavior.
- [x] Establish purpose and constraints from current approval/history: avoid manual program restart in a demo; preserve baseline/parameters/trends/animation; no automatic tare or firmware reflash.
- [x] Prepare two alternatives for the user: reopen the existing data port in the same process and replay ordinary i/s startup (recommended, closest to successful intervention), or keep port open and resend i/s (smaller interruption but independently unverified).
- [x] Present detailed design and obtain approval (可以).
- [x] Write approved design to docs/superpowers/specs/2026-09-28-coinft-stream-recovery-design.md. No Git repository: no commit claimed.
- [x] Inline spec review: no placeholders; defined silence threshold, cooldown start-to-start, real-data success, public recovery diagnostics and initial/manual tare preservation. Same-process reopen and frontend-baseline invariants agree. Scope excludes firmware/UI/tuning changes. No Git commit claimed.
- [x] Written spec approved by user (“可以”); execution choice: split-task with independent review.
- [x] writing-plans saved docs/superpowers/plans/2026-09-28-coinft-stream-recovery.md; self-review PASS.
- [x] Before snapshots saved in stream-recovery-before; focused baseline16 tests PASS.
- [x] Task1 TDD implementation and independent review (v2 Approved; actual-attempt cancellation defect fixed).
- [x] Whole-change code/spec APPROVE + independent architecture CLEAR -> software APPROVE;124 fulltestsPASS/14 protectedunchanged; software handoffprepared.
- [ ] Operator manual deploymentrestart/initialdemozero; actualsame-processphysicalrecoveryacceptance (notperformed).
- [ ] Deployment preflightBLOCKED: userstartednewPID36404 butoldPID47424 remains; both8765listeners, directAPIconnectionsownedby47424/no recoveryfield. ClosebothverifiedCoinFTconsolesandstartoncebeforeacceptance. Evidence stream-recovery-deployment-duplicate-processes-20260928.json. No servicecontrol/COM capture/forcecommands byassistant.
- [ ] Latestrecheckafter“已重新启动”: threePIDs47424/36404/37960, all8765listeners; bothdirectAPIownedbyold47424/no recovery. Evidence stream-recovery-deployment-three-processes-20260928.json. Operator firstends ONLYtheseverifiedCoinFTprocesses; confirmzeroowners BEFORE anotherstartup. NoactualassistantprocesscontrolorCOMaction.

## Implemented design boundaries (software verified; live deployment pending)

- Only the current PC acquisition reader owns/reopens the configured raw port; no second serial writer and no sensor command on COM8.
- Trigger only a silence condition: no new raw bytes and no new parsed frames for at least2s. Normal constant-value frames, sustained force, saturation or invalid-value frames alone must not trigger reconnect/zero.
- Reopen the data port and use existing i/0.2s/input-buffer reset/s startup. Maintain at least5s between recovery attempts while still stalled; cancellation must interrupt waiting and close cleanly.
- Preserve established PC projector baseline, user-page demo baseline, frame/cumulative diagnostics epochs and current tuning. Initial program startup still requires the original400-frame PC baseline; an explicitly requested tare keeps its intentional behavior. Recovery must never call request_tare on its own when a baseline already exists.
- Clear only connection-local parser pending data and reset throughput window; save fault counters before clearing. Retain absolute attempt/result diagnostics in the same server process. Surface pause/resume should reuse existing frontend behavior, not modify app.js/surface.js or chart layout.
- Do not claim recovery until new complete acceptable data reaches normal live state. Failed reconnects remain visibly waiting/error; no cached frame accepted as fresh output.
- No Teensy/CoinFT firmware changes, power cycle, USB unplug, tuning writes or changes to COM6/COM8 roles. No bypass of prior service start/stop tool restrictions; operator handles deployment restart.

## Execution record

- User execution choice: 分任务执行并独立审查（推荐）.
- Plan: docs/superpowers/plans/2026-09-28-coinft-stream-recovery.md, self-review PASS.
- Backend/test normalized text snapshots: .superpowers/sdd/stream-recovery-before. Original byte hashes: stream-recovery-source-before.json.
- Current protected hashes: stream-recovery-protected-before.json (old Teensy manifest is historical, not current batch baseline).
- Task1 worker: /root/stream_recovery_impl; owns coinft_demo.py and covering serial tests only. Full regression and deployment not yet performed.
- Task1 implementation report: stream-recovery-task-1-report.md. RED9 tests failed for missing approved behavior; GREEN recovery13+diagnostics5+core11 PASS. No production hardware/service commands.
- Controller full suite:123 tests in69.344s/exit0, stream-recovery-full-suite-v1.json. Protected14 files unchanged, stream-recovery-protected-after.json.
- Independent task review: /root/stream_recovery_task_review reviewing stream-recovery-review-v1.diff; exit/counter boundary under focused check, no verdict yet.
- Task review v1: Needs fixes, one Important actual-attempt-count/cancellation defect, noCritical/Minor. See stream-recovery-task-review-v1.md. Fresh /root/stream_recovery_fix owns surgical RED/GREEN repair; rereview required.
- Fix RED14 onlyboundaryregressionFAIL; GREEN14recovery+5diagnostics+11core/compilePASS. Re-reviewv2 Approved, zeroCritical/Important/Minor. See stream-recovery-task-review-v2.md. Backend96EF5BBE...913828; testsAECC7D7A...8B8B76.
- Fresh whole-change /root/stream_recovery_final_review underway; controller finalfullsuite rerun afterrepair in progress. Original123PASS is beforefix, notfinalcodeclaim.
- Finalfullsuiteafterfix:124 tests/68.249s/exit0, stream-recovery-full-suite-v2.json. Finalmanifest14protectedunchanged/backend96EF5BBE...913828, stream-recovery-final-manifest.json.
- Finalcode/spec/qualitylane APPROVE, zeroactionableCritical/Important/Minor, stream-recovery-code-review-final.md. Primaryfault+closeerrorcoverageclarifiedasstaticreview, notexecutedtest.
- code-reviewskill independentarchitectpreset failedunsupportedmodel; replacedby availableBackendArchitect /root/stream_recovery_architecture_review; independentarchitectevidence stillpending, nofinalsynthesisapprovalyet.
- Architecturelane returnedCLEAR withfileevidence; stream-recovery-architecture-review-final.md. Both independentlaneoutputs available, finalsoftware recommendationAPPROVE. No unresolvedactionablefindings.
- Softwarehandoff complete; runningoriginalservice wasnotrestarted/reloaded. UsermustcloseoriginalacquisitionconsoleandopenSTART_DEMOonce, keepemptyforinitial400validframes, performoneintentionalpagedemozeroifnewprocessinvalidatedit. Runtimeauto recoveryitselfdoesnotrequesttareorchangebaseline.
- NoactualCOMopened/devicecommand/firmwareupload/servicecontrol/electricalfaultinjectionbyexecutionorreview. Physicalrecoveryandpermanentrootcausefixnotclaimed.

## Evidence and limitations

Detailed proposal and written spec approved. Baseline focused tests16 PASS before production edits. Software implementation is underway; no live serial recovery commands, firmware upload or service control in this execution.

Prior stopped windows: same boot, PC read loop/main loop/timer continue, UART-consumed/packets/USB attempts flat. Release did not recover. User service-only restart then restored UART and host frame progression without evidence of Teensy reboot (starts+1/stops+2). Evidence: teensy-diagnostics-service-restart-recovered-20260928.json.

The successful intervention combined port open/close, i/s, buffer reset and PC baseline. It does not prove which action restored the stream or identify the original hardware/protocol cause. Auto-recovery is demo-continuity mitigation, not a root-cause repair claim.

## Verification to include after approval

Fake-serial/time RED-GREEN cases: quiet valid stream, exact2s silence boundary, stalled recovery and reconnect failures/cooldown, stop during retry, baseline preserved while loaded, explicit/initial tare respected, invalid/saturated frames do not trigger recovery, partial parser data and cumulative counter preservation. Existing serial/core/full UI suites must stay green; frontend hashes unchanged. Hardware acceptance only after operator manual restart, confirmed target/empty state; preserve COM8 counters at real next stop, no forced physical disconnect by assistant.
