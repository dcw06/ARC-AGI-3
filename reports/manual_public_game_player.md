# Manual public-game player with downloadable logs

The owner requested playing the games personally and downloading their own logs. The local player uses the same
archived public development versions as the retained replay: ar25, wa30, ls20 and s5i5. It executes the real offline
game engine, rather than replaying the agent or querying a model. No Kaggle or external game service is used.

Open the local page, select a game and click **Start new session**. Arrow keys map to ACTION1–4, Space to ACTION5,
board clicks to ACTION6 and Z to ACTION7. Only currently available controls are enabled. Reset is an explicit
recorded input. Coordinates are computed from the board's content area, excluding its border.

Use **Download this game's log (.jsonl)** at any point; completing the game is not necessary. **Download all logs
(.zip)** includes all saved manual sessions and the SDK's native recordings. The JSONL records contain:

| Record | Contents |
| --- | --- |
| Session start | Game/version, seed, SDK versions, UTC timestamp, initial board, actor/purpose and exposure qualification |
| Action entered | Unique request ID, action/coordinates, sequence, UTC timestamp and before-observation |
| Acknowledged action | Matching request ID/sequence, elapsed action time, after-observation and all returned frames |
| Failed/uncertain action | Error and matching request ID; further actions in that session are refused |

Observations include the legal controls, state and completed levels. Logs are flushed/fsynced after every record,
and previous sessions remain on disk when another game starts. Missing/stale/duplicate action requests and invalid
coordinates are refused. There are no automatic action retries. A session has a 2,000-input limit; a user can
download it and explicitly start another. Logs are exploratory human play after exposure to agent replays, not a
controlled naive-human benchmark or an official competition score.

The server listens only on `127.0.0.1`; mutation requests require a page token and reject other origins. The SDK
runs in OFFLINE mode with outbound Requests transport disabled. CUDA is hidden and no model runtime is imported.
Generated logs and game files must remain in a git-ignored/private directory. No recordings or private bindings
are included in this commit.

```sh
python3.12 scripts/play_public_games_manual.py --data <private-git-ignored-directory> --port 8788
```

Open `http://127.0.0.1:8788`. **Stop local player** stops the helper; saved logs remain in the data directory.
Download first if you want a browser copy, since the download endpoints stop with the service.

CPU verification covered all four real offline games, explicit reset, log contents, invalid/stale/duplicate refusal
and ZIP/native-recording export (21 checks). A separate browser service verified keyboard input, disabled controls,
cell (32,32) clicking, JSONL attachment/content and ZIP response. All test inputs are labeled automated and kept
separate from human sessions. These checks do not run a model or authorize any GPU/scored experiment.

The [official SDK](https://github.com/arcprize/arc-agi#arcade-class) documents OFFLINE mode and recording with
frame data. This player adds a local human-control interface and durable before/after action records.
