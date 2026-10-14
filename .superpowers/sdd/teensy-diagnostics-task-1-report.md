# Task 1 result: DONE_WITH_CONCERNS — frozen 2026-09-28

Conditional instrumentation implemented and native/target compilation verified. No upload, COM access, service action, package installation, Git initialization/commit/worktree, or SDK edits performed. Root owns deployment, observer and project ledger. Source is frozen pending followup authorization.

## Changed files

- C:/Users/winer/Desktop/CoinFT_Teensy_Interface/teensy_coinft_serial_interface.cpp
- C:/Users/winer/Desktop/CoinFT_Teensy_Interface/platformio.ini
- tests/teensy_diag_fixture/Arduino.h
- tests/teensy_diag_fixture/test_firmware.cpp
- tests/test_teensy_diagnostic_firmware.py
- This report.

Instrumentation compiles only under USB_DUAL_SERIAL. Appended teensy40_diag extends original teensy40 and sets -DUSB_DUAL_SERIAL. Existing tuning, commands, setup delays, baud, timer interval, UART read/end-condition order, newData timing and raw write order preserved. UART counts use actual consumed bytes; raw USB accepted counts use actual returns bounded to requested size so wrapped negative returns are excluded. Heartbeat is main-loop-only, 500ms unsigned elapsed check, open-port/whole-line-capacity guard, bounded snprintf with overflow rejection, fixed thirteen uint32 CSV fields. Sequence counts elapsed reporting attempts, including skips. No diagnostics on raw Serial.

ISR counters have one writer (ISR); other counters have one writer (main loop). Atomic snapshot masks only around three volatile reads, restoring prior PRIMASK. Teensy SDK lacks __get_PRIMASK/__set_PRIMASK, so actual ARM code uses MRS/MSR with memory clobbers plus SDK __disable_irq. Native external boundary replaces mask access; native tests do not execute ARM assembly. Actual ARM build validates assembly compilation, not hardware timing.

## TDD evidence

Read test-driven-development SKILL.md and testing-anti-patterns.md completely before implementation. Actual firmware is included into native harness; fake boundary only replaces Arduino ports, timer, time, interrupts. No production test-only methods added.

RED command before source/config modifications:

`D:/conda/python.exe -m unittest discover -s tests -p test_teensy_diagnostic_firmware.py -v`

Baseline compiled in legacy and USB_DUAL_SERIAL modes. Ran 7 tests in 4.233s, exit1: legacy protocol passed; six diagnostic cases failed with exact assertion `ASSERTION: expected CFD1 heartbeat on diagnostic port`. Not a missing-symbol or compiler failure.

After first implementation, short-return test exposed a fixture expectation error: a 5-byte short payload leaves more than the original 1ms end-scan can consume with fake micros advancing250us. Changed fixture to23-byte return, leaving two scan bytes, preserving firmware timeout semantics and still proving actual-short-return accounting. Firmware was not changed to consume extra bytes.

Additional root-requested SIZE_MAX write-failure case was introduced, observed RED (`ASSERTION: failed SIZE_MAX USB writes counted as accepted bytes`, 8 tests/1.634s/exit1), then fixed only the accepted-count arithmetic without changing writes. Final GREEN command same as RED: 9 tests in1.691s, exit0. Earlier GREEN 8 tests in1.583s, exit0.

Native compiler flags: `g++ -std=c++17 -Wall -Wextra -Werror [-DUSB_DUAL_SERIAL] -I <fixture> <fixture>/test_firmware.cpp -o <TemporaryDirectory>/<mode>.exe`. Separate subprocesses provide fresh actual firmware globals per scenario; timeout10s. Temporary binaries automatically removed.

Nine cases cover legacy protocol; diagnostic protocol/counters; initial/periodic heartbeat; closed/full port and sequence gaps; short payload/write return counts; SIZE_MAX USB write failure; end timeout/garbage header; masked IRQ state and uptime rollover; unmasked IRQ state/all UINT32_MAX values/exact maximum148-byte CSV/sequence+loop wrap. Protocol cases assert exact setup61 tuning bytes, 14 delays (500ms then thirteen50ms), baud, s/t/i forwarding,1ms timer start/end, newData reset, original26-byte raw output and UART packet consumption. Tests distinguish USB acceptance from host delivery; no host-delivery claim.

## Diagnostic target build

Command: `C:/Users/winer/.platformio/penv/Scripts/pio.exe run -d C:/Users/winer/Desktop/CoinFT_Teensy_Interface -e teensy40_diag`

Initial build failed solely because SDK does not expose CMSIS PRIMASK helpers. Local ARM assembly correction then built successfully: exit0, SUCCESS3.804s. Platform Teensy5.2.0; framework1.162.0/Teensy1.62; toolchain15.2.1; Teensy4.0 IMXRT1062 600MHz.

- FLASH code40980, data7200, headers9160, free1974276.
- RAM1 variables9088, code39256, padding26280, free locals449664.
- RAM2 variables24736, free malloc/new499552.

Original environment was never built. No further build required after final fixture-only max/wrap additions; production source unchanged from successful target build.

## Hashes and artifact preservation concern

Before editing, current source/config hashes checked against backup and matched:

- Original source CFE97D1E3E4C258A72BAE0BD49C4D7A359EBB40EF24DF01826204DD3B0618962.
- Original config 139BC8DBDEA970C97F252054C0D58C40BDA682E06B61AC5821D10A7365A5C212.
- Original backed-up hex FD53CE8129EEF078C1FB5B9068B41CD7D2F8F54D7964E3E084EBDC3F519B7788.
- Original backed-up elf FC213E3FF3F43348C88303A2D4CF9EB5A47A1979424542FE4A15F3232E343182.

Final source29638CF96C9E6AC61459AC7927C5F6D21C63787F38869D0485A672F0DCA870F0; config3B8D4F0CDF97BF2A80C16B2616518C1B9F825F711121A0D82EECBBA689EE0552.

Diagnostic hex2AB2F56FF8221EB728E4E4C897EE9717F81F96FB23FB79139ED13315C4C3FDC8; elf40C88B3AC51940FDF43FA8F84109BAB26E673726B804597D423EA302E279EFF2.

Unexpected PIO behavior: original .pio/build/teensy40 artifacts are absent after diagnostic build. Default run auto-cleans the entire build directory when project config checksum changes. Evidence: installed platformio/run/cli.py123-127 calls clean_build_dir; run/helpers.py32-41 computes project checksum and calls fs.rmtree(build_dir) on mismatch. Adding environment changed config checksum. No explicit delete/clean was issued by worker. Backup original hex/elf rehashed after build and remain identical to manifest. Root was notified to restore original two artifacts from backup and use `--disable-auto-clean` for future builds. Worker has not restored files outside listed ownership. Preservation criterion is therefore not claimed fully satisfied until root restores them. Original on-disk binaries are not certified as the currently flashed firmware; no device identity claim.

## Deployment blocker: SDK write is not certified non-waiting

Exact current open/capacity guard is implemented. However installed cores/teensy4/usb_serial2.c377-389 computes availableForWrite by summing idle transfer buffers excluding tx_head. usb_serial2_write308-347 checks/waits for current tx_head when tx_available is0 and may yield until TX_TIMEOUT_MSEC120 (definition265). Aggregate available space therefore does not prove the next current-head write never waits. No concurrent diagnostic application writer exists, but SDK buffering itself prevents a strict no-wait guarantee. SDK begin is nonblocking (wait code commented out in usb_serial.h266ff); begin was not added.

Root instructed freeze as DONE_WITH_CONCERNS and will obtain direction before deployment or authorize isolated diagnostic-only non-waiting adaptation. No weakened requirement, SDK patch, automatic recovery, ISR architecture change or upload was performed. Native test results do not establish live USB behavior, timing, force accuracy or physical fault cause.

## Approved non-waiting supplement — DONE, frozen 2026-09-28

User explicitly approved the diagnostic-only supplement. Read adapter brief and updated approved design completely before resuming. This supplement resolves the prior SDK-wait deployment blocker at the implementation/native-build boundary; hardware deployment and review remain root-owned. Root restored original teensy40 artifacts before resuming, and the supplement used --disable-auto-clean throughout. No live COM/upload/service/package/Git actions; firmware cpp remains frozen with original Task1 final hash.

Additional changed files:

- Firmware project platformio.ini: extra_scripts only under teensy40_diag.
- Firmware project scripts/diag_usb_nonblocking.py: pure exact-SHA256/unique-anchor guarded transform.
- Firmware project scripts/diag_usb_build.py: diagnostic-only AddBuildMiddleware substitution/build generation.
- coinft/tests/teensy_diag_fixture/test_usb_adapter.cpp.
- coinft/tests/test_teensy_diagnostic_usb_adapter.py.
- This report append.

Transform changes only usb_serial2_write and usb_serial2_write_buffer_free, retaining upstream bytes before/after exactly, including license, RX paths, flush implementation and original timeout declarations. SHA guard575F5852165647E39F059548AE244A4B426A8BE31BFEF57CC4A9044FA8A37A3B; missing/ambiguous anchors and wrong hash raise ValueError, never silently fallback. Middleware validates even if SCons considers target current, and tracks adapter module as a generation dependency. SDK installed files are read only.

Write checks configured/empty first; then saves and sets tx_noautoflush with compiler memory barriers. Current contiguous tx_available is used; at zero, exactly one current-head transfer status checks busy0x80/error0x68. No aggregate other-head capacity. Insufficient capacity returns0 without a prefix or head/buffer mutation. Ready write copies exact bytes in full and returns size. Partial-buffer path retains one-shot timer semantics; exact-full path retains prepare/cache/transmit/head advance+wrap/timer-stop behavior. All exits restore prior autoflush0/1. Capacity checks use the same current-head rule without claiming state or yielding. No clock wait, polling loops, yield, printf or flush in either adapted function. No latched timeout; busy-to-ready recovery is immediate. Raw usb_serial.c remains untouched and original ISR forwarding is unchanged.

### Supplemental TDD evidence

Before any production adapter/middleware edits, native harness compiled actual unmodified SDK write/capacity function text. External replacements are transfer/cache/timer/clock/yield/logging boundaries, not duplicated transmit algorithms. First RED command:

`D:/conda/python.exe -m unittest discover -s tests -p test_teensy_diagnostic_usb_adapter.py -v`

Result1 test/0.536s/exit1. Exact stderr: `busy result=0 yields=121 fake_elapsed_ms=121`, then `ASSERTION: busy-head diagnostic write must not yield`. Baseline successfully compiled; expected wait assertion failed. This represents simulated121ms, not a measured physical delay.

After adaptation, same command GREEN5 tests/1.984s/exit0. Harness now compiles actual transformed SDK function text from guarded transform. Cases: busy head with other free buffers skips without yields and capacity0; subsequent ready recovers with exact148 bytes; unconfigured; each busy/error status mask; insufficient contiguous capacity/all-or-nothing prefix; empty write; ready bytes/returns/partial timer; exact-full head wrap/DMA/cache/timer; success/failure/autoflush prior0/1 restoration; zero printf/yield; guarded mismatch/ambiguous/missing anchors; untouched source regions and current upstream hash. Native flags `g++ -std=c++17 -Wall -Wextra -I <TemporaryDirectory> <fixture>/test_usb_adapter.cpp -o <TemporaryDirectory>/adapter.exe`; functions include generated only in temporary directory. Test executable timeout5s. Original firmware fixture unchanged, rerun9 tests/1.663s/exit0.

### Actual target substitution evidence

Command: `C:/Users/winer/.platformio/penv/Scripts/pio.exe run --disable-auto-clean -d C:/Users/winer/Desktop/CoinFT_Teensy_Interface -e teensy40_diag -v`

Exit0, SUCCESS1.478s. Original teensy40 explicitly IGNORED. Output announces diagnostic substitute `.pio/build/teensy40_diag/diag_sdk/usb_serial2.c`; SCons generate step consumes installed upstream. Exact ARM compile invocation includes `arm-none-eabi-gcc -o .pio/build/teensy40_diag/diag_sdk/usb_serial2.c.o ... -DUSB_DUAL_SERIAL ... .pio/build/teensy40_diag/diag_sdk/usb_serial2.c`. Archive command includes this substitute instead of original FrameworkArduino/usb_serial2.c.o; `arm-none-eabi-ar t libFrameworkArduino.a` confirms exactly one usb_serial2.c.o member. Thus successful build actually uses adapter, with no second duplicate core object. Original core include paths preserved.

Intentional warning: original upstream `transmit_previous_timeout` now unused; retained because brief explicitly prohibits removing original timeout declarations solely for cleanup. No other build error. Object disassembly restricted to usb_serial2_write shows calls only memcpy, usb_prepare_transfer, usb_transmit, usb_transfer_status; no yield/printf. Unchanged RX SDK paths still contain upstream yields and are outside diagnostic TX adaptation.

New target sizes: FLASH code40852,data7200,headers8264,free1975300; RAM1 variables9088,code39128,padding26408,free449664; RAM2 variables24736,free499552.

### Supplemental hashes and limits

Protected pre/post unchanged:

- Global CDC2 SDK575F5852165647E39F059548AE244A4B426A8BE31BFEF57CC4A9044FA8A37A3B.
- Global raw SDK A675E0479E27CBAD3A8E0FA6B918020AF5B0F8894BE43EBC495832995F5D842C.
- Original on-disk and backup HEX FD53CE8129EEF078C1FB5B9068B41CD7D2F8F54D7964E3E084EBDC3F519B7788.
- Original on-disk and backup ELF FC213E3FF3F43348C88303A2D4CF9EB5A47A1979424542FE4A15F3232E343182.
- Task1 firmware cpp29638CF96C9E6AC61459AC7927C5F6D21C63787F38869D0485A672F0DCA870F0.
- All9 entries in root's teensy-invariants-before-adapter-20260928.json independently checked unchanged (also IMU config/demo/UI/start batch).

Supplement final config5EEC927B6834F8FF812C15CB138E99E09D828BA40E836E57619F7C9401704F60; transform module9BE047F2EDFEE8AB51F08C59527E6F9F94FBDF8E12FD9BC70190816C5BB6AF30; middleware2C9F4A1FC448DF3211EE781CDAF16CE17479AD172EC97A5A6C55549D231BBB76; generated SDK6ECB1D166079E6FF936499DC49A897AA9C361E025C8B9E313121B99D2466B2B9; diagnostic HEX582472C5472ADAE578EC928E5DD5A078F0B82C3D20B66457BADC9634A2C3C657; diagnostic ELF1D92CD3BD22DD6C50904FD4B1B6B7E5BF523645292B7B1B4A0551F21520CD500.

Original artifact preservation is now satisfied through restoration plus verified unchanged supplement build. No hardware claims: native tests simulate external transfer/timer boundaries; target build validates compilation/substitution, not physical USB enumeration, execution time, PC delivery, or device-flashed identity. Root handles review and any explicitly gated upload. Supplement source now frozen as DONE.

### Final warning annotation requested by root

Root requested minimal explicit unused-latch annotation instead of leaving compiler noise. Added `(void)transmit_previous_timeout` inside adapted write only, with a comment stating the original latch is retained without diagnostic waiting. No declaration removal or logic change. The initial warning remains documented above.

Revalidated adapter5 tests/2.044s/exit0; repeated diagnostic verbose build with --disable-auto-clean SUCCESS1.388s/exit0, generated CDC2 source compiled again, no warnings. Memory sizes unchanged. All9 protected invariant hashes rechecked unchanged after this final build. HEX unchanged582472C5472ADAE578EC928E5DD5A078F0B82C3D20B66457BADC9634A2C3C657; final ELF D2A6B0D5ACEC437BA3886F2FE8F974BDE0E4D9658BB6CB327403BB233E14DDE8 (link embeds time). Final transform49D6FFFEA85800217FB809272AAFC86D4C281090680270B94EFF402631C92849; generated SDK248A3865C67F364C7B323186249D3D74780581B5570D74E26DD912265088A958. Other hashes listed above unchanged. Final source freeze DONE; no outstanding implementation blocker found within approved scope.

## Review I1 repair — DONE, frozen 2026-09-28

Read entire Task1 review. Its sole Important finding I1 is valid: a timer expiry dispatched while tx_noautoflush=1 can be acknowledged and discarded by unchanged flush callback, leaving a partial buffer stranded. Verified actual usb.c ISR reads USB1_USBSTS and acknowledges it before calling timer1 callback (266/363); upstream flush callback returns immediately on tx_noautoflush. No other Critical/Important/Minor implementation findings were present.

Before production fix, expanded native fixture to compile actual unchanged usb_serial2_flush_callback in addition to the actual transformed write/capacity functions. Fake external one-shot expiry clears its armed state before invoking actual callback, matching acknowledged one-shot behavior; it is not an algorithm substitute. A test-only tx_available wrapper injects expiry at the protected read boundary for capacity/rejection; timer-start boundary injects success expiry. Actual callback executes prepare/cache/transmit when allowed, and fake transfer sink captures submitted byte length/content. Tests therefore prove submission of exact pending bytes, not merely timer-call counts.

RED command `D:/conda/python.exe -m unittest discover -s tests -p test_teensy_diagnostic_usb_adapter.py -v`:8 tests/3.537s/exit1; original5 passed, all3 new success/capacity/rejection expiry cases failed with exact `ASSERTION: suppressed expiry stranded partial buffer without timer retry`. The suppressed expiry executed once; no armed timer remained. Production source unchanged until this RED was observed.

Minimal repair only inside the two adapted transmit functions: restore previous tx_noautoflush, add compiler memory barrier, and rearm one-shot if a partial buffer remains (`tx_available > 0 && tx_available < TX_SIZE`). Do this on success, insufficient-space rejection and capacity exit. Move successful partial timer start outside the protected window. Full-buffer submission remains protected and has no partial timer retry; empty/unconfigured exits preserve earlier behavior. No blocking wait, flush, yield, polling, broad interrupt mask, global SDK change, firmware cpp change or raw forwarding change. Restoring prior1 continues to respect caller suppression; existing prior0/1 tests remain passing. A callback between restore and retry may already flush the bytes; a redundant empty timer is harmless. The barrier prevents compiler ordering the pending-state test before protection release.

GREEN same adapter command:8 tests/4.087s/exit0. Three new cases demonstrate exact DMA submission without another successful append: success-start expiry now occurs after protection release and submits immediately; capacity/rejection expiry is consumed while protected, then explicitly rearmed and subsequent expiry submits existing pending1948 bytes. Submitted content asserted as the exact148-byte accepted data or existing1948 bytes0xA5. All earlier current-head/no-yield/error/size/flag/hash guard cases still pass. Firmwarecpp hash unchanged; per root's scoped instruction no redundant firmware suite rerun for this adapter-only fix.

Target command `C:/Users/winer/.platformio/penv/Scripts/pio.exe run --disable-auto-clean -d C:/Users/winer/Desktop/CoinFT_Teensy_Interface -e teensy40_diag -v`:exit0, SUCCESS1.492s, no warnings. Verbose output includes regenerated `.pio/build/teensy40_diag/diag_sdk/usb_serial2.c` compile and replacement object in framework archive; original teensy40 IGNORED. FLASH code40980,data7200,headers9160,free1974276; RAM1 variables9088,code39256,padding26280,free449664; RAM2 variables24736,free499552.

Changed only transform module, adapter fixture/test and this report append. Rechecked all9 protected invariant entries after target build:PASS, including both installed SDKs/original HEX+ELF/IMU/demo/UI/start batch. Frozen firmwarecpp hash29638CF96C9E6AC61459AC7927C5F6D21C63787F38869D0485A672F0DCA870F0 unchanged. New final hashes:

- transform4097CF522362C14B832EB43DE88561BE6034A186A42CAE83D430FD58C6267C24.
- generated SDK758FBE802750988C4B4967B64D249C3E8A01A57746D46105418E985851C89DB5.
- diagnostic HEX F38E094D43F39ED01AD5C7AED172E22D6947B90226CB9B7A8EF41F810FF9C9CD.
- diagnostic ELF3AD484723F76A7C8AD26FCD09047482B9B6A1074D426C3D9DDEFBA692650C2E9.
- fixture48134B5910107363C7AC6C35A8A3D73FA89ECA5001D1C22F4F56E771C79AB482.
- adapter test0645F38E776F99287497F86FF704142F07651010C18AD35ADFE1D978572505A4.

No live COM/upload/service actions. I1 repair is implementation-complete and frozen for root's renewed review/deployment gate; hardware timing/delivery remain bench-validation limits, not claims established by native tests.
