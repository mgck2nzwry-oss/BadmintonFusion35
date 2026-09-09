# BadmintonFusion35 Desktop Player

This is a local Windows desktop application, not a browser dashboard.  It plays
four synchronized Pose2Sim 2D-skeleton camera clips while displaying synchronized
IMU and 3D-kinematic signals on the same time axis.

## Run the A01 demonstration

From PowerShell, run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\desktop_app\run_a01_demo.ps1
```

The first launch creates `desktop_app\.venv`, installs the two display
dependencies, and derives a short no-audio A01-R1 demonstration package from the
local Pose2Sim project at `E:\Pose2SimProjects\Badminton_Final`.  Generated clips
and data are kept in `desktop_app\local_assets` and are ignored by Git.

## Import another trial

The program accepts a data JSON file following the `a01-local-sync-v1` layout and
four clips named `cam01.mp4` to `cam04.mp4` in one folder.  Use **Open data JSON**
and **Open video folder** in the program.  This allows a later trial to be
processed by the same visualisation application without putting participant video
or raw measurements into the repository.

## Verification without opening a window

```powershell
.\desktop_app\run_a01_demo.ps1 -SelfTest
```

The self-test checks the generated data package, all four decodable video streams,
and the expected signal channels.

## Build a native Windows executable

After the first launch, run:

```powershell
.\desktop_app\build_desktop_exe.ps1
```

The result is `desktop_app\dist\BadmintonFusion35-Player\BadmintonFusion35-Player.exe`.
The executable remains local; `dist`, temporary build files, and generated A01
assets are excluded from Git.
