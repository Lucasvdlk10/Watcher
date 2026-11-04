# Watcher — Windows Downloads organizer

Desktop application in active development. It combines a native WinUI 3 interface with the existing local Python core over an authenticated bridge, for reviewing and organizing indexed files.

> **Development preview — Windows build and product qualification are pending.** This repository contains source only; no tested installer or release binary is included. The V4 handoff explicitly states that native Windows build, the complete test matrix, accessibility/performance review and Windows smoke tests remain unverified. The current installed V3 remains the production version; this V4 code must not replace it.

## Scope

- WinUI 3/C# front end and bridge source.
- Python core integration and test sources.
- Build, installer and rollback scripts for Windows evaluation.
- Reports documenting implemented features, assumptions and remaining acceptance gates.

## Requirements and build

The supplied handoff specifies Windows 11 x64, .NET 10, Windows App SDK 1.8.12, Visual Studio 2022 with WinUI workload, and the required Python V3 runtime. Exact SDK availability and compatibility must be checked before building. Review the scripts before running them.

The provided Windows build script is `Installer/BUILD_WINDOWS_RELEASE.ps1`. It has **not** been executed as part of this publication. Do not install this preview over V3 or point it at personal Downloads during testing. Use disposable test folders and data.

## Validation status

The project handoff reports 129 baseline tests plus 10 bridge tests as required, but does not claim V4 Windows build/homologation. No verified current test pass or executable build is claimed for this repository. See [`HANDOFF.md`](HANDOFF.md) and [`Reports/WINDOWS_QA.md`](Reports/WINDOWS_QA.md) for exact remaining gates.

## Data and privacy

The application can index local filenames and paths. This source repository excludes local runtime databases, logs, backups, user folders and prebuilt outputs. Do not commit local configuration, indexed file data or personal Download paths.

## Maturity

This is an engineering preview, not a replacement for the working V3 and not a signed or qualified Windows release. Issues and incremental commits are welcome, but any public build must be clearly labeled unverified until its Windows qualification is complete.

## Dependencies and license

Third-party and Windows SDK license terms continue to apply. This repository does not add a broad open-source license for the application source; reuse rights require an explicit license from the owner. Review dependency notices before redistribution.
