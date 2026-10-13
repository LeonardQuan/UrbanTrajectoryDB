# Educational C++ trajectory compression MVP

`cpp/compression.cpp` is a standalone C++17 standard-library-only CLI. It reads one ordered trajectory, runs iterative Douglas–Peucker, verifies the projected error, and writes retained original coordinates. It deliberately does not integrate with or change the Python Geolife parser, database, or package dependencies.

## Build and run

From the repository root, using Windows Git Bash and the available MinGW compiler:

```bash
mkdir -p cpp/build
F:/mingw64/bin/g++ -std=c++17 -O2 -Wall -Wextra -pedantic cpp/compression.cpp -o cpp/build/trajectory_compress.exe
export PATH="F:/mingw64/bin:$PATH"
cpp/build/trajectory_compress.exe --epsilon 10 < input.csv > simplified.csv 2> stats.json
cpp/build/trajectory_compress.exe --epsilon 10 --input input.csv --output simplified.csv 2> stats.json
```

On Linux/macOS, replace the compiler path with `g++` and omit `.exe`. The source uses no platform-specific APIs. A CMake build is also available:

```bash
cmake -S cpp -B cpp/build -G "MinGW Makefiles" -DCMAKE_CXX_COMPILER=F:/mingw64/bin/g++.exe -DCMAKE_MAKE_PROGRAM=F:/mingw64/bin/mingw32-make.exe
cmake --build cpp/build
```

For other platforms/generators: `cmake -S cpp -B cpp/build && cmake --build cpp/build`. Windows MinGW runtime DLLs must be discoverable in `PATH`; compiling with g++ does not itself configure the runtime search path.

## CLI contract

```text
trajectory_compress --epsilon METRES [--input CSV] [--output CSV]
```

- `--epsilon` is required, finite and non-negative; zero is valid. Unknown/duplicate options, missing values and invalid paths are errors.
- Without path flags, read stdin and write stdout. With `--output`, stdout is empty. Successful stderr contains one JSON statistics object; failures return nonzero with `error:` on stderr.
- Exact header: `longitude,latitude` (LF or CRLF). Subsequent lines contain exactly two unquoted numeric fields in that order. Scientific notation and surrounding numeric whitespace are accepted. Blank data rows, additional columns and quoted CSV fields are not supported.
- Longitude must be finite within [-180, 180]; latitude within [-90, 90]. Invalid rows identify their one-based CSV line number. Header-only input is an empty trajectory; a completely empty file is invalid.
- All input is validated and compression checked before opening the output path. Existing output files are overwritten on success; do not use shell redirection back onto the input file. Coordinates are emitted with 17 significant digits to preserve the parsed doubles, not their original text formatting.
- Empty/single/two-point trajectories retain all points. Longer trajectories always preserve both endpoint **indices**, including identical endpoint coordinates. Retained points remain in original order.
- Epsilon zero removes exactly collinear intermediate points in floating-point projected arithmetic; it is not a promise to retain every original point or every duplicate.

JSON fields:

| Field | Meaning |
| --- | --- |
| `original` | Number of input points |
| `retained` | Number of output points |
| `compression_ratio` | Fraction removed, `1 - retained/original`; zero for empty input. Not a file-size ratio. |
| `max_deviation_m` | Maximum over original vertices of their minimum distance to any returned projected segment; zero for empty/single input. |

## Geometry and guarantee boundary

The origin `(longitude0, latitude0)` and fixed reference latitude are taken from the **first input point**, not recomputed for each segment. With angles in radians and radius `R = 6371000 m`:

```text
x = R * (longitude - longitude0) * cos(latitude0)
y = R * (latitude - latitude0)
```

Distances use this local equirectangular plane. This is an **approximate local metric, not a global geodesic guarantee**. Use short, local city trajectories. Long journeys, strong latitude changes, poles (longitude scale degenerates), and antimeridian crossings are not handled as reliable metre distances. Longitude is not unwrapped. Valid geographic coordinate ranges do not imply the projection is accurate everywhere.

For each pending index interval, find the interior vertex farthest from the **finite segment**, clamping the perpendicular projection to [0,1]. A zero-length segment uses distance to its endpoint. Split only when that distance is strictly greater than epsilon. An explicit vector of pending intervals replaces recursion, avoiding recursion-stack overflow. Worst-case DP time is O(n²); projected points, keep flags, and pending intervals consume O(n) memory.

After simplification, a separate exhaustive audit measures every original vertex against every retained segment, costs O(n * retained), and refuses output if its measured maximum exceeds epsilon. Thus a successful run checks `max_deviation_m <= epsilon` in the projected double-precision plane. This is a vertex-to-polyline metric, not a symmetric Hausdorff, time-synchronized, speed-preservation, or ellipsoidal geodesic claim. Floating-point arithmetic remains subject to rounding; an unexpectedly excessive measured error fails instead of silently weakening the bound.

## Learning path

1. Follow one straight line and one bend through `project`, `distance`, and `simplify`.
2. Observe the split condition and why endpoint indices are always marked.
3. Compare epsilon 0, 1, 5, and 20; inspect retention versus verified deviation.
4. Reimplement the finite-segment distance, then reproduce the independent Python check.
5. Only after understanding these pieces consider efficient auditing or a proper regional/geodesic metric. This MVP is an understandable executable, not an overbuilt general-purpose geometry library.

## Tests and real RED/GREEN notes

Run in the existing virtual environment (the host's default `python` lacks pytest):

```bash
.venv/Scripts/python.exe -m pytest tests/test_compression.py -q
.venv/Scripts/python.exe -m pytest tests/ -q
```

The session fixture discovers `CXX` or `g++`, with a fallback to `F:/mingw64/bin/g++.exe`, compiles in pytest's temporary directory using C++17 and strict warnings, and launches the actual executable. Only absence of a compiler causes a reasoned skip. Compilation warnings/errors and missing implementation are failures, not skips. Builds and tests do not need network access. Independent Python geometry checks validate the returned polyline over several epsilon values and assert endpoint preservation and ordered original-point membership.

These are **actual execution excerpts**, not example/generated results. Each feature slice was tested before its implementation. Raw local transcripts were captured as `F:/Hermes-Official/cache/scratch/compression-{red,green}N.txt` (scratch is temporary); their outcome lines are preserved here:

| Slice | Observed RED | Observed GREEN |
| --- | --- | --- |
| 1: header-only input | `1 failed in 0.13s` — `AssertionError: compression CLI implementation is missing` | `1 passed in 5.58s` |
| 2: straight line endpoints | `1 failed, 1 passed in 0.82s` — output `[]` instead of endpoints | `2 passed in 1.26s` |
| 3: epsilon-sensitive bend | `1 failed, 2 passed in 0.94s` — middle bend incorrectly dropped | `3 passed in 2.32s` |
| 4: epsilon validation | `6 failed, 3 passed in 1.62s` — negative/nonfinite/junk accepted, empty epsilon unhandled | `9 passed in 1.71s` |
| 5: CSV validation | `16 failed, 9 passed in 1.85s` — malformed/out-of-range/nonfinite coordinates and invalid headers accepted | `25 passed in 1.51s` |
| 6: statistics and independent deviation audit | `8 failed, 27 passed in 2.60s` — absent JSON statistics (`JSONDecodeError`) | `35 passed in 1.96s` |
| 7: path arguments and CLI validation | `9 failed, 35 passed in 7.04s` — path arguments ignored and invalid usage accepted | `44 passed in 4.98s` |

Single/two-point, epsilon-zero, repeated-endpoint and backtracking regression tests were added during slice 6; their geometry already passed from the preceding DP implementation. They are not claimed as independently failing feature slices. Refactoring then fixed Python formatting/lint and C++ indentation without changing behavior.

CMake was also exercised before and after adding its build file:

```text
RED: CMake Error: The source directory "F:/UrbanTrajectoryDB/cpp" does not appear to contain CMakeLists.txt.
GREEN: [100%] Built target trajectory_compress
```

Final post-refactor execution:

```text
59 passed, 2 skipped in 9.92s
All checks passed!
[100%] Built target trajectory_compress
```

The full-suite count includes other Python MVP tests present concurrently in the repository. The two skips are opt-in real PostGIS tests (`Set URBAN_DB_TEST=1 for isolated real PostGIS tests`), not C++ skips. No live database check is claimed here.

A real CMake-built CLI run on three points `(106,29.5)`, `(106.0001,29.5001)`, `(106.0002,29.5)` with `--epsilon 20` produced:

stdout:
```csv
longitude,latitude
106,29.5
106.00020000000001,29.5
```

stderr:
```json
{"original":3,"retained":2,"compression_ratio":0.33333333333333337,"max_deviation_m":11.119492664429957}
```

Only `cpp/`, `tests/test_compression.py`, and this document belong to the compression change. Existing step-08 parser edits and other concurrent work are preserved; no commit or push was performed.
