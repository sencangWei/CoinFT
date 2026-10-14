param(
    [Parameter(Mandatory=$true)][string]$BaselineJson,
    [switch]$PrepareOnly
)

# Read-only observation: never serial, tare, or page zero.
$demoBaseline = [double[]]($BaselineJson | ConvertFrom-Json)
if ($demoBaseline.Count -ne 12) { throw 'Expected 12 baseline channels' }
$demoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$demoProfile = Get-Content -Raw -Encoding UTF8 (Join-Path $demoRoot 'demo_web\shear_demo_profile.json') | ConvertFrom-Json
if ($PrepareOnly) {
    $demoState = Invoke-RestMethod -Uri http://127.0.0.1:8765/api/state -TimeoutSec 2
    [pscustomobject]@{prepared=$true;status=$demoState.status;frame=$demoState.frames;rate=$demoState.rate;baseline=$demoBaseline;duration=5;automatic_zero=$false} | ConvertTo-Json -Compress
    exit
}
$demoSamples = [System.Collections.Generic.List[object]]::new()
$demoErrors = [System.Collections.Generic.List[object]]::new()
$demoTimer = [System.Diagnostics.Stopwatch]::StartNew()
while ($demoTimer.Elapsed.TotalSeconds -lt 5) {
    try {
        $demoState = Invoke-RestMethod -Uri http://127.0.0.1:8765/api/state -TimeoutSec 1
        if ($demoState.channels.Count -ne 12) { throw 'Malformed channels' }
        $delta = @(for ($i=0; $i -lt 12; $i++) { [double]$demoState.channels[$i] - [double]$demoBaseline[$i] })
        $normalSorted = @($delta[8..11] | Sort-Object)
        $normal = [Math]::Max([double]0, [double](($normalSorted[1]+$normalSorted[2])/2))
        $avg = ($delta[0..7] | Measure-Object -Average).Average
        $rawShear = 0.0
        $shear = 0.0
        for ($i=0; $i -lt 8; $i++) {
            $rawShear += $demoProfile.shear.weights[$i]*($delta[$i]-$avg)
            $shear += $demoProfile.shear.weights[$i]*($delta[$i]-$avg-$demoProfile.shear.pressLeak[$i]*$normal)
        }
        $normalTarget = [Math]::Max([double]0,[Math]::Min([double]1,[double](($normal-$demoProfile.normal.threshold)/$demoProfile.normal.span)))
        $shearTarget = [Math]::Sign($shear)*[Math]::Max([double]0,[Math]::Min([double]1,[double](([Math]::Abs($shear)-$demoProfile.shear.threshold)/$demoProfile.shear.span)))
        $demoSamples.Add([pscustomobject]@{elapsed=$demoTimer.Elapsed.TotalSeconds;frame=$demoState.frames;status=$demoState.status;invalid_recent=$demoState.invalid_recent;saturated_recent=$demoState.saturated_recent;normal=$normal;rawShear=$rawShear;shear=$shear;normalTarget=$normalTarget;shearTarget=$shearTarget;channels=$demoState.channels;raw=$demoState.raw})
    } catch {
        $demoErrors.Add([pscustomobject]@{elapsed=$demoTimer.Elapsed.TotalSeconds;error=$_.Exception.Message})
    }
    Start-Sleep -Milliseconds 100
}
[pscustomobject]@{pose='operator-confirmed center press + minus-X';baseline=$demoBaseline;samples=$demoSamples;errors=$demoErrors;elapsed=$demoTimer.Elapsed.TotalSeconds;threshold=$demoProfile.shear.threshold;span=$demoProfile.shear.span} | ConvertTo-Json -Depth 6 -Compress
