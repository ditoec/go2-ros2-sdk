# Bluetooth Speaker Output (TTS)

`tts_node` speaks through a connected Bluetooth speaker when one is available and
falls back to the robot's own speaker otherwise. The choice is made per utterance,
so connecting or powering off a speaker takes effect at runtime — no restart.

| Env var | Default | Meaning |
|---|---|---|
| `TTS_BLUETOOTH` | `true` | `false` → always use the robot speaker |
| `TTS_BLUETOOTH_SINK` | `bluez_sink` | substring matched against PulseAudio sink names |
| `TTS_BLUETOOTH_PROBE_SEC` | `5.0` | how often the sink list is re-checked |
| `PULSE_SERVER` | `tcp:127.0.0.1:4713` | how the container reaches the host's PulseAudio |

## Why the container needs `PULSE_SERVER`

BlueZ and PulseAudio run on the **host**; the ROS2 stack runs in the **container**.
Because the container uses `network_mode: host`, exposing PulseAudio on loopback TCP
is enough — no socket bind-mount or cookie sharing required.

Run once on the host:

```bash
pactl load-module module-native-protocol-tcp listen=127.0.0.1 auth-anonymous=1
```

Persist it by appending the same `load-module ...` line to `/etc/pulse/default.pa`.
`listen=127.0.0.1` keeps the socket off the LAN; only host-local processes
(including host-network containers) can reach it.

The container image already ships `pactl`, `paplay` and libpulse, so no rebuild is needed.

## Jetson / JetPack: two extra fixes

Stock JetPack cannot do Bluetooth audio at all. Both fixes are host-side and permanent.

**1. JetPack disables the A2DP plugin.** `/usr/lib/systemd/system/bluetooth.service.d/nv-bluetooth-service.conf`
starts `bluetoothd -d --noplugin=audio,a2dp,avrcp`, so `org.bluez.Media1.RegisterEndpoint()`
does not exist. Symptom: pairing succeeds but `bluetoothctl connect` returns
`org.bluez.Error.NotAvailable`, and PulseAudio logs `UnknownMethod`.

Create a drop-in with the **same filename** under `/etc/` to mask NVIDIA's:

```ini
# /etc/systemd/system/bluetooth.service.d/nv-bluetooth-service.conf
[Service]
ExecStart=
ExecStart=/usr/lib/bluetooth/bluetoothd
```

Then `sudo systemctl daemon-reload && sudo systemctl restart bluetooth`.

**2. PulseAudio must stay resident.** Install the module and stop the daemon exiting on idle,
or the A2DP sink disappears roughly every 30 s (visible as repeated
`Endpoint registered` / `unregistered` pairs in `journalctl -u bluetooth`):

```bash
sudo apt-get install -y pulseaudio-module-bluetooth
sudo sed -i 's/^\s*;\?\s*exit-idle-time.*/exit-idle-time = -1/' /etc/pulse/daemon.conf
sudo loginctl enable-linger <user>     # PulseAudio must survive without a login session
```

## Pairing a speaker

```bash
bluetoothctl --timeout 20 scan on
bluetoothctl pair <MAC> && bluetoothctl trust <MAC> && bluetoothctl connect <MAC>
pactl list sinks short | grep bluez     # confirm the A2DP sink exists
```

`trust` matters: it lets the speaker reconnect on its own when powered on.

### Combo Wi-Fi/Bluetooth dongles

On a shared-radio dongle (e.g. Realtek RTL8821CU) Bluetooth discovery can return
**zero** devices while Wi-Fi carries active traffic — including an interactive SSH
session over that same adapter. Run scan/pair/connect detached and read the log
afterwards, so the link is idle during the Bluetooth operation:

```bash
nohup timeout 45 bluetoothctl --timeout 40 scan on > /tmp/btscan.log 2>&1 &
# ...wait, then inspect /tmp/btscan.log
```

## Troubleshooting

| Symptom | Cause |
|---|---|
| `org.bluez.Error.NotAvailable` on connect | A2DP plugin disabled (JetPack fix 1) or `pulseaudio-module-bluetooth` missing |
| Sink appears then vanishes every ~30 s | `exit-idle-time` not set to `-1` |
| `pactl` works on host, not in container | `PULSE_SERVER` unset, or the TCP module is not loaded |
| Scanning finds nothing | Wi-Fi/BT coexistence — run detached (see above) |
| TTS still uses the robot speaker | check `tts_node` startup line: `Playback: Bluetooth if connected, else Robot` |

---

# Audio Input Priority

`stt_node` picks its microphone in priority order and re-checks every
`STT_SOURCE_PROBE_SEC` (default 10 s), so connecting a mic takes effect without a restart:

| Tier | Source | Matched by |
|---|---|---|
| 1 | Bluetooth headset mic | `bluez_source.*` |
| 2 | USB mic on the Jetson | `alsa_input.usb-*` |
| 3 | Robot's own mic (`/robot_audio`) | fallback when neither exists |

Set `STT_SOURCE=auto` (the default). `STT_SOURCE_PRIORITY` reorders tiers 1–2;
`STT_SOURCE=mic` or `=robot` pins one source explicitly.

Tiers 1–2 are captured with `parec` against the host's PulseAudio (`PULSE_SERVER`),
the same channel the TTS output uses. Monitor sources are always skipped, so a
connected Bluetooth *speaker* is never mistaken for a microphone — without that,
the robot would hear its own TTS.

## This only applies to `stt_node`

It requires `MIC_BRIDGE=false`. With `MIC_BRIDGE=true` the capture node is
`mic_bridge_node`, which has its own two sources (browser mic over WebSocket, or
`/robot_audio`) and does not open local audio devices at all.

## Bluetooth mic caveat (tier 1)

A Bluetooth **mic** requires the headset's HSP/HFP profile. Two consequences:

1. **HSP/HFP cannot coexist with A2DP.** They are separate profiles on the same
   card, so enabling the mic switches output to mono narrowband — TTS drops to
   phone-call quality. High-fidelity playback and Bluetooth mic input are mutually
   exclusive on classic Bluetooth.
2. **Many devices report HSP as unavailable.** On PulseAudio 13 the native backend
   supports HSP only; full HFP needs oFono. Check with:

   ```bash
   pactl list cards | grep -A2 headset_head_unit
   ```

   `available: no` means the mic cannot be used. Forcing it fails:

   ```
   $ pactl set-card-profile bluez_card.XX headset_head_unit
   Failure: Input/Output error
   ```

   Tier 1 then simply never selects, and tier 2 or 3 is used instead — no error,
   no configuration change needed.
