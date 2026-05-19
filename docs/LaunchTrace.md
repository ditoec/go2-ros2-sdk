ollama      | 2026-05-18 11:48:31.388 | time=2026-05-18T04:48:31.388Z level=INFO source=routes.go:1802 msg="server config" env="map[CUDA_VISIBLE_DEVICES: GGML_VK_VISIBLE_DEVICES: GPU_DEVICE_ORDINAL: HIP_VISIBLE_DEVICES: HSA_OVERRIDE_GFX_VERSION: HTTPS_PROXY: HTTP_PROXY: NO_PROXY: OLLAMA_CONTEXT_LENGTH:0 OLLAMA_DEBUG:INFO OLLAMA_DEBUG_LOG_REQUESTS:false OLLAMA_EDITOR: OLLAMA_FLASH_ATTENTION:false OLLAMA_GPU_OVERHEAD:0 OLLAMA_HOST:http://0.0.0.0:11434 OLLAMA_KEEP_ALIVE:5m0s OLLAMA_KV_CACHE_TYPE: OLLAMA_LLM_LIBRARY: OLLAMA_LOAD_TIMEOUT:5m0s OLLAMA_MAX_LOADED_MODELS:0 OLLAMA_MAX_QUEUE:512 OLLAMA_MAX_TRANSFER_STREAMS:4 OLLAMA_MODELS:/root/.ollama/models OLLAMA_MULTIUSER_CACHE:false OLLAMA_NEW_ENGINE:false OLLAMA_NOHISTORY:false OLLAMA_NOPRUNE:false OLLAMA_NO_CLOUD:false OLLAMA_NUM_PARALLEL:1 OLLAMA_ORIGINS:[http://localhost https://localhost http://localhost:* https://localhost:* http://127.0.0.1 https://127.0.0.1 http://127.0.0.1:* https://127.0.0.1:* http://0.0.0.0 https://0.0.0.0 http://0.0.0.0:* https://0.0.0.0:* app://* file://* tauri://* vscode-webview://* vscode-file://*] OLLAMA_REMOTES:[ollama.com] OLLAMA_SCHED_SPREAD:false OLLAMA_VULKAN:false ROCR_VISIBLE_DEVICES: http_proxy: https_proxy: no_proxy:]"
ollama      | 2026-05-18 11:48:31.388 | time=2026-05-18T04:48:31.388Z level=INFO source=routes.go:1804 msg="Ollama cloud disabled: false"
ollama      | 2026-05-18 11:48:31.389 | time=2026-05-18T04:48:31.388Z level=INFO source=images.go:517 msg="total blobs: 4"
ollama      | 2026-05-18 11:48:31.389 | time=2026-05-18T04:48:31.389Z level=INFO source=images.go:524 msg="total unused blobs removed: 0"
ollama      | 2026-05-18 11:48:31.389 | time=2026-05-18T04:48:31.389Z level=INFO source=routes.go:1864 msg="Listening on [::]:11434 (version 0.24.0)"
ollama      | 2026-05-18 11:48:31.391 | time=2026-05-18T04:48:31.391Z level=INFO source=runner.go:67 msg="discovering available GPUs..."
ollama      | 2026-05-18 11:48:31.392 | time=2026-05-18T04:48:31.391Z level=INFO source=server.go:433 msg="starting runner" cmd="/usr/bin/ollama runner --ollama-engine --port 46077"
ollama      | 2026-05-18 11:48:31.640 | time=2026-05-18T04:48:31.640Z level=INFO source=server.go:433 msg="starting runner" cmd="/usr/bin/ollama runner --ollama-engine --port 37623"
ollama      | 2026-05-18 11:48:31.731 | time=2026-05-18T04:48:31.731Z level=INFO source=runner.go:106 msg="experimental Vulkan support disabled.  To enable, set OLLAMA_VULKAN=1"
ollama      | 2026-05-18 11:48:31.732 | time=2026-05-18T04:48:31.731Z level=INFO source=server.go:433 msg="starting runner" cmd="/usr/bin/ollama runner --ollama-engine --port 33193"
ollama      | 2026-05-18 11:48:31.927 | time=2026-05-18T04:48:31.927Z level=INFO source=types.go:42 msg="inference compute" id=GPU-b274baec-a7dc-fa49-769c-86304a258000 filter_id="" library=CUDA compute=8.6 name=CUDA0 description="NVIDIA GeForce RTX 3070 Laptop GPU" libdirs=ollama,cuda_v12 driver=12.3 pci_id=0000:01:00.0 type=discrete total="8.0 GiB" available="7.8 GiB"
ollama      | 2026-05-18 11:48:31.927 | time=2026-05-18T04:48:31.927Z level=INFO source=routes.go:1914 msg="vram-based default context" total_vram="8.0 GiB" default_num_ctx=4096
ollama      | 2026-05-18 11:48:32.392 | time=2026-05-18T04:48:32.392Z level=INFO source=model_recommendations.go:177 msg="model recommendations cache sleep scheduled" wait=4h47m43.359883521s consecutive_failures=0
ollama      | 2026-05-18 11:48:36.448 | [GIN] 2026/05/18 - 04:48:36 | 200 |      52.526µs |       127.0.0.1 | HEAD     "/"
ollama      | 2026-05-18 11:48:36.448 | [GIN] 2026/05/18 - 04:48:36 | 200 |     250.265µs |       127.0.0.1 | GET      "/api/tags"
ollama      | 2026-05-18 11:48:37.100 | [GIN] 2026/05/18 - 04:48:37 | 200 |      27.916µs |      172.18.0.3 | HEAD     "/"
ollama_init | 2026-05-18 11:48:39.614 | pulling manifest ⠋ pulling manifest ⠙ pulling manifest ⠹ pulling manifest ⠸ pulling manifest ⠼ pulling manifest ⠴ pulling manifest ⠦ pulling manifest ⠧ pulling manifest ⠇ pulling manifest ⠏ pulling manifest ⠋ pulling manifest ⠙ pulling manifest ⠹ pulling manifest ⠸ pulling manifest ⠼ pulling manifest ⠴ pulling manifest ⠦ pulling manifest ⠧ pulling manifest ⠇ pulling manifest ⠏ pulling manifest ⠋ pulling manifest ⠙ pulling manifest ⠹ pulling manifest ⠸ pulling manifest ⠼ pulling manifest 
ollama_init | 2026-05-18 11:48:39.614 | pulling 4c27e0f5b5ad: 100% ▕██████████████████▏ 9.6 GB                         
ollama_init | 2026-05-18 11:48:39.614 | pulling 7339fa418c9a: 100% ▕██████████████████▏  11 KB                         
ollama_init | 2026-05-18 11:48:39.614 | pulling 56380ca2ab89: 100% ▕██████████████████▏   42 B                         
ollama_init | 2026-05-18 11:48:39.614 | pulling f0988ff50a24: 100% ▕██████████████████▏  473 B                         
ollama_init | 2026-05-18 11:48:39.614 | verifying sha256 digest 
ollama_init | 2026-05-18 11:48:39.614 | writing manifest 
ollama_init | 2026-05-18 11:48:39.614 | success 
ollama      | 2026-05-18 11:48:39.614 | [GIN] 2026/05/18 - 04:48:39 | 200 |  2.513216886s |      172.18.0.3 | POST     "/api/pull"
go2_ros2    | 2026-05-18 11:48:41.645 | (EE) 
go2_ros2    | 2026-05-18 11:48:41.645 | Fatal server error:
go2_ros2    | 2026-05-18 11:48:41.645 | (EE) Server is already active for display 1
go2_ros2    | 2026-05-18 11:48:41.645 | 	If this server is no longer running, remove /tmp/.X1-lock
go2_ros2    | 2026-05-18 11:48:41.645 | 	and start again.
go2_ros2    | 2026-05-18 11:48:41.645 | (EE) 
go2_ros2    | 2026-05-18 11:48:42.643 | VNC server started — connect to localhost:5901 with password 'ros2vnc'
go2_ros2    | 2026-05-18 11:48:42.643 | Mode: SIMULATION (USE_SIM=true)
go2_ros2    | 2026-05-18 11:48:42.644 | /usr/bin/startxfce4: X server already running on display :1
go2_ros2    | 2026-05-18 11:48:42.650 | xrdb: Connection refused
go2_ros2    | 2026-05-18 11:48:42.650 | xrdb: Can't open display ':1'
go2_ros2    | 2026-05-18 11:48:42.651 | 
go2_ros2    | 2026-05-18 11:48:42.651 | 18/05/2026 04:48:42 ***************************************
go2_ros2    | 2026-05-18 11:48:42.651 | 18/05/2026 04:48:42 *** XOpenDisplay failed (:1)
go2_ros2    | 2026-05-18 11:48:42.651 | 
go2_ros2    | 2026-05-18 11:48:42.651 | *** x11vnc was unable to open the X DISPLAY: ":1", it cannot continue.
go2_ros2    | 2026-05-18 11:48:42.651 | *** There may be "Xlib:" error messages above with details about the failure.
go2_ros2    | 2026-05-18 11:48:42.651 | 
go2_ros2    | 2026-05-18 11:48:42.651 | Some tips and guidelines:
go2_ros2    | 2026-05-18 11:48:42.651 | 
go2_ros2    | 2026-05-18 11:48:42.651 | ** An X server (the one you wish to view) must be running before x11vnc is
go2_ros2    | 2026-05-18 11:48:42.651 |    started: x11vnc does not start the X server.  (however, see the -create
go2_ros2    | 2026-05-18 11:48:42.651 |    option if that is what you really want).
go2_ros2    | 2026-05-18 11:48:42.651 | 
go2_ros2    | 2026-05-18 11:48:42.651 | ** You must use -display <disp>, -OR- set and export your $DISPLAY
go2_ros2    | 2026-05-18 11:48:42.651 |    environment variable to refer to the display of the desired X server.
go2_ros2    | 2026-05-18 11:48:42.651 |  - Usually the display is simply ":0" (in fact x11vnc uses this if you forget
go2_ros2    | 2026-05-18 11:48:42.651 |    to specify it), but in some multi-user situations it could be ":1", ":2",
go2_ros2    | 2026-05-18 11:48:42.651 |    or even ":137".  Ask your administrator or a guru if you are having
go2_ros2    | 2026-05-18 11:48:42.651 |    difficulty determining what your X DISPLAY is.
go2_ros2    | 2026-05-18 11:48:42.651 | 
go2_ros2    | 2026-05-18 11:48:42.651 | ** Next, you need to have sufficient permissions (Xauthority) 
go2_ros2    | 2026-05-18 11:48:42.651 |    to connect to the X DISPLAY.   Here are some Tips:
go2_ros2    | 2026-05-18 11:48:42.651 | 
go2_ros2    | 2026-05-18 11:48:42.651 |  - Often, you just need to run x11vnc as the user logged into the X session.
go2_ros2    | 2026-05-18 11:48:42.651 |    So make sure to be that user when you type x11vnc.
go2_ros2    | 2026-05-18 11:48:42.651 |  - Being root is usually not enough because the incorrect MIT-MAGIC-COOKIE
go2_ros2    | 2026-05-18 11:48:42.651 |    file may be accessed.  The cookie file contains the secret key that
go2_ros2    | 2026-05-18 11:48:42.651 |    allows x11vnc to connect to the desired X DISPLAY.
go2_ros2    | 2026-05-18 11:48:42.651 |  - You can explicitly indicate which MIT-MAGIC-COOKIE file should be used
go2_ros2    | 2026-05-18 11:48:42.651 |    by the -auth option, e.g.:
go2_ros2    | 2026-05-18 11:48:42.652 |        x11vnc -auth /home/someuser/.Xauthority -display :0
go2_ros2    | 2026-05-18 11:48:42.652 |        x11vnc -auth /tmp/.gdmzndVlR -display :0
go2_ros2    | 2026-05-18 11:48:42.652 |    you must have read permission for the auth file.
go2_ros2    | 2026-05-18 11:48:42.652 |    See also '-auth guess' and '-findauth' discussed below.
go2_ros2    | 2026-05-18 11:48:42.652 | 
go2_ros2    | 2026-05-18 11:48:42.652 | ** If NO ONE is logged into an X session yet, but there is a greeter login
go2_ros2    | 2026-05-18 11:48:42.652 |    program like "gdm", "kdm", "xdm", or "dtlogin" running, you will need
go2_ros2    | 2026-05-18 11:48:42.652 |    to find and use the raw display manager MIT-MAGIC-COOKIE file.
go2_ros2    | 2026-05-18 11:48:42.652 |    Some examples for various display managers:
go2_ros2    | 2026-05-18 11:48:42.652 | 
go2_ros2    | 2026-05-18 11:48:42.652 |      gdm:     -auth /var/gdm/:0.Xauth
go2_ros2    | 2026-05-18 11:48:42.652 |               -auth /var/lib/gdm/:0.Xauth
go2_ros2    | 2026-05-18 11:48:42.652 |      kdm:     -auth /var/lib/kdm/A:0-crWk72
go2_ros2    | 2026-05-18 11:48:42.652 |               -auth /var/run/xauth/A:0-crWk72
go2_ros2    | 2026-05-18 11:48:42.652 |      xdm:     -auth /var/lib/xdm/authdir/authfiles/A:0-XQvaJk
go2_ros2    | 2026-05-18 11:48:42.652 |      dtlogin: -auth /var/dt/A:0-UgaaXa
go2_ros2    | 2026-05-18 11:48:42.652 | 
go2_ros2    | 2026-05-18 11:48:42.652 |    Sometimes the command "ps wwwwaux | grep auth" can reveal the file location.
go2_ros2    | 2026-05-18 11:48:42.652 | 
go2_ros2    | 2026-05-18 11:48:42.652 |    Starting with x11vnc 0.9.9 you can have it try to guess by using:
go2_ros2    | 2026-05-18 11:48:42.652 | 
go2_ros2    | 2026-05-18 11:48:42.652 |               -auth guess
go2_ros2    | 2026-05-18 11:48:42.652 | 
go2_ros2    | 2026-05-18 11:48:42.652 |    (see also the x11vnc -findauth option.)
go2_ros2    | 2026-05-18 11:48:42.652 | 
go2_ros2    | 2026-05-18 11:48:42.652 |    Only root will have read permission for the file, and so x11vnc must be run
go2_ros2    | 2026-05-18 11:48:42.652 |    as root (or copy it).  The random characters in the filenames will of course
go2_ros2    | 2026-05-18 11:48:42.652 |    change and the directory the cookie file resides in is system dependent.
go2_ros2    | 2026-05-18 11:48:42.652 | 
go2_ros2    | 2026-05-18 11:48:42.652 | See also: http://www.karlrunge.com/x11vnc/faq.html
go2_ros2    | 2026-05-18 11:48:42.704 | xfce4-session: Cannot open display: .
go2_ros2    | 2026-05-18 11:48:42.704 | Type 'xfce4-session --help' for usage.
go2_ros2    | 2026-05-18 11:48:42.984 | [INFO] [launch]: All log files can be found below /root/.ros/log/2026-05-18-04-48-42-982406-58bd4d7bd85c-1
go2_ros2    | 2026-05-18 11:48:42.984 | [INFO] [launch]: Default logging verbosity is set to INFO
go2_ros2    | 2026-05-18 11:48:43.924 | [INFO] [gazebo-1]: process started with pid [70]
go2_ros2    | 2026-05-18 11:48:43.926 | [INFO] [robot_state_publisher-2]: process started with pid [72]
go2_ros2    | 2026-05-18 11:48:43.926 | [INFO] [robot_state_publisher-3]: process started with pid [73]
go2_ros2    | 2026-05-18 11:48:43.927 | [INFO] [create-4]: process started with pid [74]
go2_ros2    | 2026-05-18 11:48:43.927 | [INFO] [parameter_bridge-5]: process started with pid [75]
go2_ros2    | 2026-05-18 11:48:43.929 | [INFO] [parameter_bridge-6]: process started with pid [76]
go2_ros2    | 2026-05-18 11:48:43.929 | [INFO] [image_bridge-7]: process started with pid [77]
go2_ros2    | 2026-05-18 11:48:43.929 | [INFO] [cmd_vel_pub.py-8]: process started with pid [78]
go2_ros2    | 2026-05-18 11:48:43.929 | [INFO] [robot_controller_gazebo.py-9]: process started with pid [79]
go2_ros2    | 2026-05-18 11:48:43.929 | [INFO] [QuadrupedOdometryNode.py-10]: process started with pid [80]
go2_ros2    | 2026-05-18 11:48:43.929 | [INFO] [relay-11]: process started with pid [81]
go2_ros2    | 2026-05-18 11:48:43.929 | [INFO] [relay-12]: process started with pid [82]
go2_ros2    | 2026-05-18 11:48:43.929 | [INFO] [relay-13]: process started with pid [83]
go2_ros2    | 2026-05-18 11:48:43.930 | [INFO] [relay-14]: process started with pid [84]
go2_ros2    | 2026-05-18 11:48:43.930 | [INFO] [relay-15]: process started with pid [85]
go2_ros2    | 2026-05-18 11:48:43.931 | [INFO] [sim_cmd_node.py-16]: process started with pid [88]
go2_ros2    | 2026-05-18 11:48:43.931 | [INFO] [joy_node-17]: process started with pid [89]
go2_ros2    | 2026-05-18 11:48:43.931 | [INFO] [teleop_node-18]: process started with pid [90]
go2_ros2    | 2026-05-18 11:48:43.932 | [INFO] [twist_mux-19]: process started with pid [91]
go2_ros2    | 2026-05-18 11:48:43.932 | [INFO] [rviz2-20]: process started with pid [94]
go2_ros2    | 2026-05-18 11:48:43.933 | [INFO] [foxglove_bridge-21]: process started with pid [97]
go2_ros2    | 2026-05-18 11:48:43.933 | [INFO] [async_slam_toolbox_node-22]: process started with pid [100]
go2_ros2    | 2026-05-18 11:48:43.933 | [INFO] [controller_server-23]: process started with pid [101]
go2_ros2    | 2026-05-18 11:48:43.933 | [INFO] [smoother_server-24]: process started with pid [108]
go2_ros2    | 2026-05-18 11:48:43.934 | [INFO] [planner_server-25]: process started with pid [113]
go2_ros2    | 2026-05-18 11:48:43.934 | [INFO] [route_server-26]: process started with pid [126]
go2_ros2    | 2026-05-18 11:48:43.934 | [INFO] [behavior_server-27]: process started with pid [164]
go2_ros2    | 2026-05-18 11:48:43.934 | [INFO] [bt_navigator-28]: process started with pid [179]
go2_ros2    | 2026-05-18 11:48:43.934 | [INFO] [waypoint_follower-29]: process started with pid [198]
go2_ros2    | 2026-05-18 11:48:43.935 | [INFO] [velocity_smoother-30]: process started with pid [234]
go2_ros2    | 2026-05-18 11:48:43.939 | [INFO] [collision_monitor-31]: process started with pid [245]
go2_ros2    | 2026-05-18 11:48:43.939 | [INFO] [opennav_docking-32]: process started with pid [251]
go2_ros2    | 2026-05-18 11:48:43.939 | [INFO] [lifecycle_manager-33]: process started with pid [265]
go2_ros2    | 2026-05-18 11:48:43.939 | [INFO] [mic_bridge_node-34]: process started with pid [279]
go2_ros2    | 2026-05-18 11:48:43.939 | [INFO] [voice_cmd_node-35]: process started with pid [297]
go2_ros2    | 2026-05-18 11:48:43.954 | [rviz2-20] qt.qpa.xcb: could not connect to display :1
go2_ros2    | 2026-05-18 11:48:43.954 | [rviz2-20] qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.
go2_ros2    | 2026-05-18 11:48:43.954 | [rviz2-20] This application failed to start because no Qt platform plugin could be initialized. Reinstalling the application may fix this problem.
go2_ros2    | 2026-05-18 11:48:43.954 | [rviz2-20] 
go2_ros2    | 2026-05-18 11:48:43.954 | [rviz2-20] Available platform plugins are: eglfs, linuxfb, minimal, minimalegl, offscreen, vnc, xcb.
go2_ros2    | 2026-05-18 11:48:43.954 | [rviz2-20] 
go2_ros2    | 2026-05-18 11:48:44.120 | [create-4] [INFO] [1779079724.109069534] [spawn_go2]: Requesting list of world names.
go2_ros2    | 2026-05-18 11:48:44.449 | [planner_server-25] [INFO] [1779079724.448447864] [planner_server]: 
go2_ros2    | 2026-05-18 11:48:44.451 | [planner_server-25] 	planner_server lifecycle node launched. 
go2_ros2    | 2026-05-18 11:48:44.454 | [planner_server-25] 	Waiting on external lifecycle transitions to activate
go2_ros2    | 2026-05-18 11:48:44.455 | [planner_server-25] 	See https://design.ros2.org/articles/node_lifecycle.html for more information.
go2_ros2    | 2026-05-18 11:48:44.465 | [planner_server-25] [INFO] [1779079724.457140684] [planner_server]: Creating
go2_ros2    | 2026-05-18 11:48:44.536 | [ERROR] [rviz2-20]: process has died [pid 94, exit code -6, cmd '/opt/ros/jazzy/lib/rviz2/rviz2 -d /ros2_ws/install/go2_robot_sdk/share/go2_robot_sdk/config/single_robot_conf_sim.rviz --ros-args -r __node:=go2_rviz2 --params-file /tmp/launch_params_z7cbvc4b'].
go2_ros2    | 2026-05-18 11:48:44.539 | [gazebo-1] qt.qpa.xcb: could not connect to display :1
go2_ros2    | 2026-05-18 11:48:44.539 | [gazebo-1] qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.
go2_ros2    | 2026-05-18 11:48:44.539 | [gazebo-1] This application failed to start because no Qt platform plugin could be initialized. Reinstalling the application may fix this problem.
go2_ros2    | 2026-05-18 11:48:44.539 | [gazebo-1] 
go2_ros2    | 2026-05-18 11:48:44.539 | [gazebo-1] Available platform plugins are: eglfs, linuxfb, minimal, minimalegl, offscreen, vnc, xcb.
go2_ros2    | 2026-05-18 11:48:44.539 | [gazebo-1] 
go2_ros2    | 2026-05-18 11:48:44.539 | [gazebo-1] Stack trace (most recent call last):
go2_ros2    | 2026-05-18 11:48:44.539 | [bt_navigator-28] [INFO] [1779079724.538044723] [bt_navigator]: 
go2_ros2    | 2026-05-18 11:48:44.540 | [bt_navigator-28] 	bt_navigator lifecycle node launched. 
go2_ros2    | 2026-05-18 11:48:44.540 | [bt_navigator-28] 	Waiting on external lifecycle transitions to activate
go2_ros2    | 2026-05-18 11:48:44.540 | [bt_navigator-28] 	See https://design.ros2.org/articles/node_lifecycle.html for more information.
go2_ros2    | 2026-05-18 11:48:44.541 | [bt_navigator-28] [INFO] [1779079724.540546073] [bt_navigator]: Creating
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #31   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x7f7f2a098152, in ruby_run_node
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #30   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x7f7f2a093e2b, in 
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #29   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x7f7f2a236b49, in rb_vm_exec
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #28   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x7f7f2a23362b, in 
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #27   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x7f7f2a22f13e, in 
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #26   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x7f7f2a22c92f, in 
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #25   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x7f7f2a16d049, in 
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #24   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x7f7f2a0961d6, in rb_protect
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #23   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x7f7f2a23b2d9, in rb_yield
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #22   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x7f7f2a236b49, in rb_vm_exec
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #21   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x7f7f2a23362b, in 
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #20   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x7f7f2a22f13e, in 
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #19   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x7f7f2a22c92f, in 
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #18   Object "/usr/lib/x86_64-linux-gnu/ruby/3.2.0/fiddle.so", at 0x7f7f253c7b13, in 
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #17   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x7f7f2a1f537b, in rb_nogvl
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #16   Object "/usr/lib/x86_64-linux-gnu/ruby/3.2.0/fiddle.so", at 0x7f7f253c743b, in 
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #15   Object "/usr/lib/x86_64-linux-gnu/libffi.so.8", at 0x7f7f253bb0bd, in ffi_call
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #14   Object "/usr/lib/x86_64-linux-gnu/libffi.so.8", at 0x7f7f253b83ee, in 
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #13   Object "/usr/lib/x86_64-linux-gnu/libffi.so.8", at 0x7f7f253bbb15, in 
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #12   Object "/opt/ros/jazzy/opt/gz_sim_vendor/lib/libgz-sim8-gz.so.8.11.0", at 0x7f7f2484fdb2, in runGui
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #11   Object "/opt/ros/jazzy/opt/gz_sim_vendor/lib/libgz-sim8-gui.so.8", at 0x7f7f2469c33c, in gz::sim::v8::gui::runGui(int&, char**, char const*, char const*, int, char const*, char const*)
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #10   Object "/opt/ros/jazzy/opt/gz_sim_vendor/lib/libgz-sim8-gui.so.8", at 0x7f7f246996d9, in gz::sim::v8::gui::createGui(int&, char**, char const*, char const*, bool, char const*, int, char const*, char const*)
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #9    Object "/opt/ros/jazzy/opt/gz_gui_vendor/lib/libgz-gui8.so.8", at 0x7f7f233fefdc, in gz::gui::Application::Application(int&, char**, gz::gui::WindowType, char const*)
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #8    Object "/usr/lib/x86_64-linux-gnu/libQt5Widgets.so.5", at 0x7f7f22e7f5b4, in QApplicationPrivate::init()
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #7    Object "/usr/lib/x86_64-linux-gnu/libQt5Gui.so.5", at 0x7f7f21d56b9e, in QGuiApplicationPrivate::init()
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #6    Object "/usr/lib/x86_64-linux-gnu/libQt5Core.so.5", at 0x7f7f23744ff4, in QCoreApplicationPrivate::init()
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #5    Object "/usr/lib/x86_64-linux-gnu/libQt5Gui.so.5", at 0x7f7f21d53c1f, in QGuiApplicationPrivate::createEventDispatcher()
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #4    Object "/usr/lib/x86_64-linux-gnu/libQt5Gui.so.5", at 0x7f7f21d536dc, in QGuiApplicationPrivate::createPlatformIntegration()
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #3    Object "/usr/lib/x86_64-linux-gnu/libQt5Core.so.5", at 0x7f7f234f7103, in QMessageLogger::fatal(char const*, ...) const
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #2    Object "/usr/lib/x86_64-linux-gnu/libc.so.6", at 0x7f7f29c308fe, in abort
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #1    Object "/usr/lib/x86_64-linux-gnu/libc.so.6", at 0x7f7f29c4d27d, in gsignal
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] #0    Object "/usr/lib/x86_64-linux-gnu/libc.so.6", at 0x7f7f29ca6b2c, in pthread_kill
go2_ros2    | 2026-05-18 11:48:44.559 | [gazebo-1] Aborted (Signal sent by tkill() 562 0)
go2_ros2    | 2026-05-18 11:48:44.604 | [robot_state_publisher-2] [INFO] [1779079724.602269567] [go2_robot_state_publisher]: Robot initialized
go2_ros2    | 2026-05-18 11:48:44.627 | [lifecycle_manager-33] [INFO] [1779079724.625370714] [lifecycle_manager_navigation]: Creating
go2_ros2    | 2026-05-18 11:48:44.688 | [robot_state_publisher-3] [INFO] [1779079724.686561875] [go2.go2_robot_state_publisher_ns]: Robot initialized
go2_ros2    | 2026-05-18 11:48:44.697 | [smoother_server-24] [INFO] [1779079724.696822885] [smoother_server]: 
go2_ros2    | 2026-05-18 11:48:44.697 | [smoother_server-24] 	smoother_server lifecycle node launched. 
go2_ros2    | 2026-05-18 11:48:44.697 | [smoother_server-24] 	Waiting on external lifecycle transitions to activate
go2_ros2    | 2026-05-18 11:48:44.697 | [smoother_server-24] 	See https://design.ros2.org/articles/node_lifecycle.html for more information.
go2_ros2    | 2026-05-18 11:48:44.711 | [smoother_server-24] [INFO] [1779079724.710076797] [smoother_server]: Creating smoother server
go2_ros2    | 2026-05-18 11:48:44.717 | [lifecycle_manager-33] [INFO] [1779079724.713661240] [lifecycle_manager_navigation]: Creating and initializing lifecycle service clients
go2_ros2    | 2026-05-18 11:48:44.770 | [teleop_node-18] [INFO] [1779079724.769389489] [TeleopTwistJoy]: Linear axis x on 1 at scale 0.500000.
go2_ros2    | 2026-05-18 11:48:44.770 | [teleop_node-18] [INFO] [1779079724.769479284] [TeleopTwistJoy]: Linear axis y on 3 at scale 0.500000.
go2_ros2    | 2026-05-18 11:48:44.770 | [teleop_node-18] [INFO] [1779079724.769486487] [TeleopTwistJoy]: Angular axis yaw on 6 at scale 1.000000.
go2_ros2    | 2026-05-18 11:48:44.938 | [twist_mux-19] [INFO] [1779079724.934386269] [twist_mux]: Topic handler 'topics.foxglove' subscribed to topic 'cmd_vel_foxglove': timeout = 0.500000s , priority = 8.
go2_ros2    | 2026-05-18 11:48:44.983 | [velocity_smoother-30] [INFO] [1779079724.981160654] [velocity_smoother]: 
go2_ros2    | 2026-05-18 11:48:44.983 | [velocity_smoother-30] 	velocity_smoother lifecycle node launched. 
go2_ros2    | 2026-05-18 11:48:44.983 | [velocity_smoother-30] 	Waiting on external lifecycle transitions to activate
go2_ros2    | 2026-05-18 11:48:44.983 | [velocity_smoother-30] 	See https://design.ros2.org/articles/node_lifecycle.html for more information.
go2_ros2    | 2026-05-18 11:48:44.992 | [twist_mux-19] [INFO] [1779079724.986084548] [twist_mux]: Topic handler 'topics.joy' subscribed to topic 'cmd_vel_joy': timeout = 0.500000s , priority = 10.
go2_ros2    | 2026-05-18 11:48:45.044 | [twist_mux-19] [INFO] [1779079725.039338750] [twist_mux]: Topic handler 'topics.navigation' subscribed to topic 'cmd_vel': timeout = 0.500000s , priority = 5.
go2_ros2    | 2026-05-18 11:48:45.065 | [twist_mux-19] [INFO] [1779079725.064532100] [twist_mux]: Topic handler 'topics.voice' subscribed to topic 'cmd_vel_voice': timeout = 0.500000s , priority = 7.
go2_ros2    | 2026-05-18 11:48:45.079 | [async_slam_toolbox_node-22] [INFO] [1779079725.066792295] [slam_toolbox]: Node using stack size 40000000
go2_ros2    | 2026-05-18 11:48:45.101 | [waypoint_follower-29] [INFO] [1779079725.098054311] [waypoint_follower]: 
go2_ros2    | 2026-05-18 11:48:45.101 | [waypoint_follower-29] 	waypoint_follower lifecycle node launched. 
go2_ros2    | 2026-05-18 11:48:45.101 | [waypoint_follower-29] 	Waiting on external lifecycle transitions to activate
go2_ros2    | 2026-05-18 11:48:45.101 | [waypoint_follower-29] 	See https://design.ros2.org/articles/node_lifecycle.html for more information.
go2_ros2    | 2026-05-18 11:48:45.103 | [waypoint_follower-29] [INFO] [1779079725.100145976] [waypoint_follower]: Creating
go2_ros2    | 2026-05-18 11:48:45.106 | [planner_server-25] [INFO] [1779079725.101051641] [global_costmap.global_costmap]: 
go2_ros2    | 2026-05-18 11:48:45.106 | [planner_server-25] 	global_costmap lifecycle node launched. 
go2_ros2    | 2026-05-18 11:48:45.107 | [planner_server-25] 	Waiting on external lifecycle transitions to activate
go2_ros2    | 2026-05-18 11:48:45.107 | [planner_server-25] 	See https://design.ros2.org/articles/node_lifecycle.html for more information.
go2_ros2    | 2026-05-18 11:48:45.110 | [planner_server-25] [INFO] [1779079725.103636365] [global_costmap.global_costmap]: Creating Costmap
go2_ros2    | 2026-05-18 11:48:45.154 | [parameter_bridge-6] [INFO] [1779079725.146665633] [go2_gz_bridge_sensors]: Creating GZ->ROS Bridge: [/go2/imu_plugin/out (gz.msgs.IMU) -> /go2/imu_plugin/out (sensor_msgs/msg/Imu)] (Lazy 0)
go2_ros2    | 2026-05-18 11:48:45.164 | [sim_cmd_node.py-16] [INFO] [1779079725.162812038] [sim_cmd_node]: sim_cmd_node ready — publish go2_interfaces/msg/WebRtcReq to /sim_cmd
go2_ros2    | 2026-05-18 11:48:45.174 | [parameter_bridge-6] [INFO] [1779079725.172229460] [go2_gz_bridge_sensors]: Creating ROS->GZ Bridge: [/go2/imu_plugin/out (sensor_msgs/msg/Imu) -> /go2/imu_plugin/out (gz.msgs.IMU)] (Lazy 0)
go2_ros2    | 2026-05-18 11:48:45.177 | [controller_server-23] [INFO] [1779079725.172722475] [controller_server]: 
go2_ros2    | 2026-05-18 11:48:45.177 | [controller_server-23] 	controller_server lifecycle node launched. 
go2_ros2    | 2026-05-18 11:48:45.177 | [controller_server-23] 	Waiting on external lifecycle transitions to activate
go2_ros2    | 2026-05-18 11:48:45.177 | [controller_server-23] 	See https://design.ros2.org/articles/node_lifecycle.html for more information.
go2_ros2    | 2026-05-18 11:48:45.184 | [parameter_bridge-6] [INFO] [1779079725.183114837] [go2_gz_bridge_sensors]: Creating GZ->ROS Bridge: [/go2/scan (gz.msgs.LaserScan) -> /go2/scan (sensor_msgs/msg/LaserScan)] (Lazy 0)
go2_ros2    | 2026-05-18 11:48:45.187 | [controller_server-23] [INFO] [1779079725.186574337] [controller_server]: Creating controller server
go2_ros2    | 2026-05-18 11:48:45.189 | [parameter_bridge-6] [INFO] [1779079725.187028616] [go2_gz_bridge_sensors]: Creating ROS->GZ Bridge: [/go2/scan (sensor_msgs/msg/LaserScan) -> /go2/scan (gz.msgs.LaserScan)] (Lazy 0)
go2_ros2    | 2026-05-18 11:48:45.189 | [behavior_server-27] [INFO] [1779079725.187355676] [behavior_server]: 
go2_ros2    | 2026-05-18 11:48:45.189 | [behavior_server-27] 	behavior_server lifecycle node launched. 
go2_ros2    | 2026-05-18 11:48:45.189 | [behavior_server-27] 	Waiting on external lifecycle transitions to activate
go2_ros2    | 2026-05-18 11:48:45.189 | [behavior_server-27] 	See https://design.ros2.org/articles/node_lifecycle.html for more information.
go2_ros2    | 2026-05-18 11:48:45.190 | [parameter_bridge-6] [INFO] [1779079725.189342467] [go2_gz_bridge_sensors]: Creating GZ->ROS Bridge: [/go2/color/image_raw (gz.msgs.Image) -> /go2/color/image_raw (sensor_msgs/msg/Image)] (Lazy 0)
go2_ros2    | 2026-05-18 11:48:45.212 | [parameter_bridge-6] [INFO] [1779079725.211231420] [go2_gz_bridge_sensors]: Creating ROS->GZ Bridge: [/go2/color/image_raw (sensor_msgs/msg/Image) -> /go2/color/image_raw (gz.msgs.Image)] (Lazy 0)
go2_ros2    | 2026-05-18 11:48:45.228 | [parameter_bridge-6] [INFO] [1779079725.226831446] [go2_gz_bridge_sensors]: Creating GZ->ROS Bridge: [/go2/color/camera_info (gz.msgs.CameraInfo) -> /go2/color/camera_info (sensor_msgs/msg/CameraInfo)] (Lazy 0)
go2_ros2    | 2026-05-18 11:48:45.238 | [parameter_bridge-6] [INFO] [1779079725.232552153] [go2_gz_bridge_sensors]: Creating ROS->GZ Bridge: [/go2/color/camera_info (sensor_msgs/msg/CameraInfo) -> /go2/color/camera_info (gz.msgs.CameraInfo)] (Lazy 0)
go2_ros2    | 2026-05-18 11:48:45.238 | [collision_monitor-31] [INFO] [1779079725.236190728] [collision_monitor]: 
go2_ros2    | 2026-05-18 11:48:45.238 | [collision_monitor-31] 	collision_monitor lifecycle node launched. 
go2_ros2    | 2026-05-18 11:48:45.238 | [collision_monitor-31] 	Waiting on external lifecycle transitions to activate
go2_ros2    | 2026-05-18 11:48:45.238 | [collision_monitor-31] 	See https://design.ros2.org/articles/node_lifecycle.html for more information.
go2_ros2    | 2026-05-18 11:48:45.377 | [mic_bridge_node-34] [INFO] [1779079725.375550685] [mic_bridge_node]: MicBridge STT: Gemma local (gemma4:e4b via http://ollama:11434)
go2_ros2    | 2026-05-18 11:48:45.386 | [controller_server-23] [INFO] [1779079725.382344801] [local_costmap.local_costmap]: 
go2_ros2    | 2026-05-18 11:48:45.387 | [controller_server-23] 	local_costmap lifecycle node launched. 
go2_ros2    | 2026-05-18 11:48:45.388 | [controller_server-23] 	Waiting on external lifecycle transitions to activate
go2_ros2    | 2026-05-18 11:48:45.388 | [controller_server-23] 	See https://design.ros2.org/articles/node_lifecycle.html for more information.
go2_ros2    | 2026-05-18 11:48:45.388 | [controller_server-23] [INFO] [1779079725.383491220] [local_costmap.local_costmap]: Creating Costmap
go2_ros2    | 2026-05-18 11:48:45.388 | [mic_bridge_node-34] [INFO] [1779079725.382356628] [mic_bridge_node]: MicBridge HTTP on port 8888
go2_ros2    | 2026-05-18 11:48:45.388 | [mic_bridge_node-34] [INFO] [1779079725.385746099] [mic_bridge_node]: mic_bridge_node ready — open http://localhost:8888 in your host browser
go2_ros2    | 2026-05-18 11:48:45.393 | [foxglove_bridge-21] [INFO] [1779079725.390834660] [foxglove_bridge]: Starting foxglove_bridge (jazzy, 3.2.6@)
go2_ros2    | 2026-05-18 11:48:45.410 | [foxglove_bridge-21] [INFO] [1779079725.409659079] [foxglove_bridge]: Server listening on port 8765
go2_ros2    | 2026-05-18 11:48:45.415 | [foxglove_bridge-21] [INFO] [1779079725.413443163] [foxglove_bridge]: Advertising new channel 1 for topic "/tf_static"
go2_ros2    | 2026-05-18 11:48:45.420 | [foxglove_bridge-21] [INFO] [1779079725.417858157] [foxglove_bridge]: Advertising new channel 2 for topic "/slam_toolbox/transition_event"
go2_ros2    | 2026-05-18 11:48:45.422 | [foxglove_bridge-21] [INFO] [1779079725.418287347] [foxglove_bridge]: Advertising new channel 3 for topic "/planner_server/transition_event"
go2_ros2    | 2026-05-18 11:48:45.426 | [foxglove_bridge-21] [INFO] [1779079725.418426474] [foxglove_bridge]: Advertising new channel 4 for topic "/tf"
go2_ros2    | 2026-05-18 11:48:45.426 | [foxglove_bridge-21] [INFO] [1779079725.420263449] [foxglove_bridge]: Advertising new channel 5 for topic "/joy/set_feedback"
go2_ros2    | 2026-05-18 11:48:45.426 | [foxglove_bridge-21] [INFO] [1779079725.420665561] [foxglove_bridge]: Advertising new channel 6 for topic "/go2_camera/color/image_raw"
go2_ros2    | 2026-05-18 11:48:45.432 | [mic_bridge_node-34] [INFO] [1779079725.423128396] [mic_bridge_node]: MicBridge WebSocket on port 8889
go2_ros2    | 2026-05-18 11:48:45.435 | [foxglove_bridge-21] [INFO] [1779079725.424564732] [foxglove_bridge]: Advertising new channel 7 for topic "/go2/robot_description"
go2_ros2    | 2026-05-18 11:48:45.436 | [foxglove_bridge-21] [INFO] [1779079725.425255849] [foxglove_bridge]: Advertising new channel 8 for topic "/smoother_server/transition_event"
go2_ros2    | 2026-05-18 11:48:45.439 | [foxglove_bridge-21] [INFO] [1779079725.429125315] [foxglove_bridge]: Advertising new channel 9 for topic "/parameter_events"
go2_ros2    | 2026-05-18 11:48:45.440 | [foxglove_bridge-21] [INFO] [1779079725.429539484] [foxglove_bridge]: Advertising new channel 10 for topic "/go2/joint_states"
go2_ros2    | 2026-05-18 11:48:45.441 | [foxglove_bridge-21] [INFO] [1779079725.430017975] [foxglove_bridge]: Advertising new channel 11 for topic "/go2/color/image_raw/compressed"
go2_ros2    | 2026-05-18 11:48:45.442 | [foxglove_bridge-21] [INFO] [1779079725.430054402] [foxglove_bridge]: Advertising new channel 12 for topic "/go2/color/image_raw"
go2_ros2    | 2026-05-18 11:48:45.442 | [foxglove_bridge-21] [INFO] [1779079725.431208281] [foxglove_bridge]: Advertising new channel 13 for topic "/rosout"
go2_ros2    | 2026-05-18 11:48:45.442 | [foxglove_bridge-21] [INFO] [1779079725.432641907] [foxglove_bridge]: Advertising new channel 14 for topic "/diagnostics"
go2_ros2    | 2026-05-18 11:48:45.444 | [foxglove_bridge-21] [INFO] [1779079725.438116806] [foxglove_bridge]: Advertising new channel 15 for topic "/clock"
go2_ros2    | 2026-05-18 11:48:45.448 | [async_slam_toolbox_node-22] [INFO] [1779079725.442477524] [slam_toolbox]: Configuring
go2_ros2    | 2026-05-18 11:48:45.500 | [route_server-26] [INFO] [1779079725.496560125] [route_server]: 
go2_ros2    | 2026-05-18 11:48:45.500 | [route_server-26] 	route_server lifecycle node launched. 
go2_ros2    | 2026-05-18 11:48:45.500 | [route_server-26] 	Waiting on external lifecycle transitions to activate
go2_ros2    | 2026-05-18 11:48:45.500 | [route_server-26] 	See https://design.ros2.org/articles/node_lifecycle.html for more information.
go2_ros2    | 2026-05-18 11:48:45.535 | [robot_controller_gazebo.py-9] [INFO] [1779079725.533870093] [go2.quadruped_controller]: Переключено на TROT контроллер
go2_ros2    | 2026-05-18 11:48:45.543 | [async_slam_toolbox_node-22] [INFO] [1779079725.542382365] [slam_toolbox]: Using solver plugin solver_plugins::CeresSolver
go2_ros2    | 2026-05-18 11:48:45.576 | [async_slam_toolbox_node-22] [INFO] [1779079725.573802930] [slam_toolbox]: CeresSolver: Using SCHUR_JACOBI preconditioner.
go2_ros2    | 2026-05-18 11:48:45.633 | [opennav_docking-32] [INFO] [1779079725.631551803] [docking_server]: 
go2_ros2    | 2026-05-18 11:48:45.633 | [opennav_docking-32] 	docking_server lifecycle node launched. 
go2_ros2    | 2026-05-18 11:48:45.633 | [opennav_docking-32] 	Waiting on external lifecycle transitions to activate
go2_ros2    | 2026-05-18 11:48:45.633 | [opennav_docking-32] 	See https://design.ros2.org/articles/node_lifecycle.html for more information.
go2_ros2    | 2026-05-18 11:48:45.633 | [opennav_docking-32] [INFO] [1779079725.631810508] [docking_server]: Creating docking_server
go2_ros2    | 2026-05-18 11:48:45.699 | [voice_cmd_node-35] [INFO] [1779079725.697958938] [voice_cmd_node]: NLU: Gemma local (gemma4:e4b via http://ollama:11434)
go2_ros2    | 2026-05-18 11:48:45.702 | [voice_cmd_node-35] [INFO] [1779079725.699823773] [voice_cmd_node]: voice_cmd_node ready — mode=simulation, cmd_topic=/sim_cmd, nlu=gemma_local
go2_ros2    | 2026-05-18 11:48:45.711 | [QuadrupedOdometryNode.py-10] [INFO] [1779079725.700228592] [quadruped_odom]: Dog Odometry Node has been started.
go2_ros2    | 2026-05-18 11:48:45.770 | [lifecycle_manager-33] [INFO] [1779079725.769382236] [lifecycle_manager_navigation]: Starting managed nodes bringup...
go2_ros2    | 2026-05-18 11:48:45.770 | [lifecycle_manager-33] [INFO] [1779079725.769504212] [lifecycle_manager_navigation]: Configuring controller_server
go2_ros2    | 2026-05-18 11:48:45.770 | [controller_server-23] [INFO] [1779079725.770235741] [controller_server]: Configuring controller interface
go2_ros2    | 2026-05-18 11:48:45.770 | [controller_server-23] [INFO] [1779079725.770278071] [controller_server]: getting progress checker plugins..
go2_ros2    | 2026-05-18 11:48:45.771 | [controller_server-23] [INFO] [1779079725.770781093] [controller_server]: getting goal checker plugins..
go2_ros2    | 2026-05-18 11:48:45.777 | [controller_server-23] [INFO] [1779079725.770940430] [controller_server]: Controller frequency set to 3.0000Hz
go2_ros2    | 2026-05-18 11:48:45.777 | [controller_server-23] [INFO] [1779079725.770991669] [local_costmap.local_costmap]: Configuring
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] Received world [/ros2_ws/install/go2_sim/share/go2_sim/worlds/cafe.world] from the GUI.
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] Gazebo Sim Server v8.11.0
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] Loading SDF world file[/ros2_ws/install/go2_sim/share/go2_sim/worlds/cafe.world].
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] Serving entity system service on [/entity/system/add]
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] Create service on [/world/default/create_multiple] (async)
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] Create service on [/world/default/create_multiple/blocking] (blocking)
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] Remove service on [/world/default/remove] (async)
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] Remove service on [/world/default/remove/blocking] (blocking)
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] Pose service on [/world/default/set_pose] (async)
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] Pose service on [/world/default/set_pose/blocking] (blocking)
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] Pose service on [/world/default/set_pose_vector] (async)
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] Pose service on [/world/default/set_pose_vector/blocking] (blocking)
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] Light configuration service on [/world/default/light_config] (async)
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] Light configuration service on [/world/default/light_config/blocking] (blocking)
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] Physics service on [/world/default/set_physics] (async)
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] Physics service on [/world/default/set_physics/blocking] (blocking)
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] SphericalCoordinates service on [/world/default/set_spherical_coordinates] (async)
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] SphericalCoordinates service on [/world/default/set_spherical_coordinates/blocking] (blocking)
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] Enable collision service on [/world/default/enable_collision] (async)
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] Enable collision service on [/world/default/enable_collision/blocking] (blocking)
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] Disable collision service on [/world/default/disable_collision] (async)
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] Disable collision service on [/world/default/disable_collision/blocking] (blocking)
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] Material service on [/world/default/visual_config] (async)
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] Material service on [/world/default/visual_config/blocking] (blocking)
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] Material service on [/world/default/wheel_slip] (async)
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] Material service on [/world/default/wheel_slip/blocking] (blocking)
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] Loaded level [default]
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] Serving world controls on [/world/default/control], [/world/default/control/state] and [/world/default/playback/control]
go2_ros2    | 2026-05-18 11:48:45.800 | [gazebo-1] [Msg] Serving GUI information on [/world/default/gui/info]
go2_ros2    | 2026-05-18 11:48:45.823 | [INFO] [launch.user]: [LifecycleLaunch] Slamtoolbox node is activating.
go2_ros2    | 2026-05-18 11:48:45.826 | [controller_server-23] [INFO] [1779079725.824447356] [local_costmap.local_costmap]: Using plugin "static_layer"
go2_ros2    | 2026-05-18 11:48:45.829 | [async_slam_toolbox_node-22] [INFO] [1779079725.827627182] [slam_toolbox]: Activating
go2_ros2    | 2026-05-18 11:48:45.835 | [controller_server-23] [INFO] [1779079725.834074394] [local_costmap.local_costmap]: Subscribing to the map topic (/map) with transient local durability
go2_ros2    | 2026-05-18 11:48:45.844 | [controller_server-23] [INFO] [1779079725.843289602] [local_costmap.local_costmap]: Initialized plugin "static_layer"
go2_ros2    | 2026-05-18 11:48:45.844 | [controller_server-23] [INFO] [1779079725.843420856] [local_costmap.local_costmap]: Using plugin "voxel_layer"
go2_ros2    | 2026-05-18 11:48:45.852 | [controller_server-23] [INFO] [1779079725.851893253] [local_costmap.local_costmap]: Subscribed to Topics: scan
go2_ros2    | 2026-05-18 11:48:45.910 | [create-4] [INFO] [1779079725.909727153] [spawn_go2]: Waiting messages on topic [/robot_description].
go2_ros2    | 2026-05-18 11:48:45.915 | [controller_server-23] [INFO] [1779079725.914979746] [local_costmap.local_costmap]: Initialized plugin "voxel_layer"
go2_ros2    | 2026-05-18 11:48:45.916 | [controller_server-23] [INFO] [1779079725.915069839] [local_costmap.local_costmap]: Using plugin "inflation_layer"
go2_ros2    | 2026-05-18 11:48:45.921 | [controller_server-23] [INFO] [1779079725.917308820] [local_costmap.local_costmap]: Initialized plugin "inflation_layer"
go2_ros2    | 2026-05-18 11:48:45.936 | [create-4] [INFO] [1779079725.933728037] [spawn_go2]: Entity creation successful.
go2_ros2    | 2026-05-18 11:48:45.944 | [parameter_bridge-5] [INFO] [1779079725.941208439] [go2_gz_bridge_clock]: Creating GZ->ROS Bridge: [/clock (gz.msgs.Clock) -> /clock (rosgraph_msgs/msg/Clock)] (Lazy 0)
go2_ros2    | 2026-05-18 11:48:46.037 | [controller_server-23] [INFO] [1779079726.035000468] [controller_server]: Created progress_checker : progress_checker of type nav2_controller::SimpleProgressChecker
go2_ros2    | 2026-05-18 11:48:46.041 | [controller_server-23] [INFO] [1779079726.039545806] [controller_server]: Controller Server has progress_checker  progress checkers available.
go2_ros2    | 2026-05-18 11:48:46.044 | [controller_server-23] [INFO] [1779079726.041639175] [controller_server]: Created goal checker : general_goal_checker of type nav2_controller::SimpleGoalChecker
go2_ros2    | 2026-05-18 11:48:46.046 | [controller_server-23] [INFO] [1779079726.042636208] [controller_server]: Controller Server has general_goal_checker  goal checkers available.
go2_ros2    | 2026-05-18 11:48:46.049 | [controller_server-23] [INFO] [1779079726.048674953] [controller_server]: Created controller : FollowPath of type dwb_core::DWBLocalPlanner
go2_ros2    | 2026-05-18 11:48:46.054 | [controller_server-23] [INFO] [1779079726.051013137] [controller_server]: Setting transform_tolerance to 0.200000
go2_ros2    | 2026-05-18 11:48:46.091 | [controller_server-23] [INFO] [1779079726.091068072] [controller_server]: Using critic "RotateToGoal" (dwb_critics::RotateToGoalCritic)
go2_ros2    | 2026-05-18 11:48:46.099 | [controller_server-23] [INFO] [1779079726.098767245] [controller_server]: Critic plugin initialized
go2_ros2    | 2026-05-18 11:48:46.104 | [controller_server-23] [INFO] [1779079726.101300709] [controller_server]: Using critic "Oscillation" (dwb_critics::OscillationCritic)
go2_ros2    | 2026-05-18 11:48:46.104 | [controller_server-23] [INFO] [1779079726.103273398] [controller_server]: Critic plugin initialized
go2_ros2    | 2026-05-18 11:48:46.104 | [controller_server-23] [INFO] [1779079726.103537082] [controller_server]: Using critic "BaseObstacle" (dwb_critics::BaseObstacleCritic)
go2_ros2    | 2026-05-18 11:48:46.104 | [controller_server-23] [INFO] [1779079726.103839248] [controller_server]: Critic plugin initialized
go2_ros2    | 2026-05-18 11:48:46.105 | [controller_server-23] [INFO] [1779079726.104000707] [controller_server]: Using critic "GoalAlign" (dwb_critics::GoalAlignCritic)
go2_ros2    | 2026-05-18 11:48:46.109 | [controller_server-23] [INFO] [1779079726.107636656] [controller_server]: Critic plugin initialized
go2_ros2    | 2026-05-18 11:48:46.110 | [controller_server-23] [INFO] [1779079726.108421792] [controller_server]: Using critic "PathAlign" (dwb_critics::PathAlignCritic)
go2_ros2    | 2026-05-18 11:48:46.115 | [controller_server-23] [INFO] [1779079726.112433778] [controller_server]: Critic plugin initialized
go2_ros2    | 2026-05-18 11:48:46.117 | [controller_server-23] [INFO] [1779079726.112643281] [controller_server]: Using critic "PathDist" (dwb_critics::PathDistCritic)
go2_ros2    | 2026-05-18 11:48:46.117 | [controller_server-23] [INFO] [1779079726.114916346] [controller_server]: Critic plugin initialized
go2_ros2    | 2026-05-18 11:48:46.117 | [controller_server-23] [INFO] [1779079726.115649917] [controller_server]: Using critic "GoalDist" (dwb_critics::GoalDistCritic)
go2_ros2    | 2026-05-18 11:48:46.117 | [INFO] [create-4]: process has finished cleanly [pid 74]
go2_ros2    | 2026-05-18 11:48:46.119 | [controller_server-23] [INFO] [1779079726.118341424] [controller_server]: Critic plugin initialized
go2_ros2    | 2026-05-18 11:48:46.119 | [controller_server-23] [INFO] [1779079726.118535482] [controller_server]: Controller Server has FollowPath  controllers available.
go2_ros2    | 2026-05-18 11:48:46.166 | [lifecycle_manager-33] [INFO] [1779079726.165962114] [lifecycle_manager_navigation]: Configuring smoother_server
go2_ros2    | 2026-05-18 11:48:46.167 | [smoother_server-24] [INFO] [1779079726.166499995] [smoother_server]: Configuring smoother server
go2_ros2    | 2026-05-18 11:48:46.208 | [smoother_server-24] [INFO] [1779079726.207147684] [smoother_server]: Created smoother : simple_smoother of type nav2_smoother::SimpleSmoother
go2_ros2    | 2026-05-18 11:48:46.213 | [smoother_server-24] [INFO] [1779079726.212116768] [smoother_server]: Smoother Server has simple_smoother  smoothers available.
go2_ros2    | 2026-05-18 11:48:46.507 | [gazebo-1] [Msg] World [default] initialized with [default_physics] physics profile.
go2_ros2    | 2026-05-18 11:48:46.507 | [gazebo-1] [Msg] Serving world SDF generation service on [/world/default/generate_world_sdf]
go2_ros2    | 2026-05-18 11:48:46.507 | [gazebo-1] [Msg] Serving world names on [/gazebo/worlds]
go2_ros2    | 2026-05-18 11:48:46.507 | [gazebo-1] [Msg] Resource path add service on [/gazebo/resource_paths/add].
go2_ros2    | 2026-05-18 11:48:46.507 | [gazebo-1] [Msg] Resource path get service on [/gazebo/resource_paths/get].
go2_ros2    | 2026-05-18 11:48:46.507 | [gazebo-1] [Msg] Resource path resolve service on [/gazebo/resource_paths/resolve].
go2_ros2    | 2026-05-18 11:48:46.507 | [gazebo-1] [Msg] Resource paths published on [/gazebo/resource_paths].
go2_ros2    | 2026-05-18 11:48:46.507 | [gazebo-1] [Msg] Server control service on [/server_control].
go2_ros2    | 2026-05-18 11:48:46.507 | [gazebo-1] [Msg] Found no publishers on /stats, adding root stats topic
go2_ros2    | 2026-05-18 11:48:46.507 | [gazebo-1] [Msg] Found no publishers on /clock, adding root clock topic
go2_ros2    | 2026-05-18 11:48:46.508 | [gazebo-1] Warning [Utils.cc:132] [/sdf/model[@name="robot"]/link[@name="base_link"]/sensor[@name="camera"]/gz_frame_id:<urdf-string>:L0]: XML Element[gz_frame_id], child of element[sensor], not defined in SDF. Copying[gz_frame_id] as children of [sensor].
go2_ros2    | 2026-05-18 11:48:46.508 | [gazebo-1] Warning [Utils.cc:132] [/sdf/model[@name="robot"]/link[@name="base_link"]/sensor[@name="imu_sensor"]/gz_frame_id:<urdf-string>:L0]: XML Element[gz_frame_id], child of element[sensor], not defined in SDF. Copying[gz_frame_id] as children of [sensor].
go2_ros2    | 2026-05-18 11:48:46.509 | [gazebo-1] Warning [Utils.cc:132] [/sdf/model[@name="robot"]/link[@name="base_link"]/sensor[@name="laser"]/gz_frame_id:<urdf-string>:L0]: XML Element[gz_frame_id], child of element[sensor], not defined in SDF. Copying[gz_frame_id] as children of [sensor].
go2_ros2    | 2026-05-18 11:48:46.591 | [foxglove_bridge-21] [INFO] [1779079726.590536869] [foxglove_bridge]: Advertising new channel 16 for topic "/transformed_global_plan"
go2_ros2    | 2026-05-18 11:48:46.591 | [foxglove_bridge-21] [INFO] [1779079726.590624236] [foxglove_bridge]: Advertising new channel 17 for topic "/speech_text"
go2_ros2    | 2026-05-18 11:48:46.592 | [foxglove_bridge-21] [INFO] [1779079726.591063629] [foxglove_bridge]: Advertising new channel 18 for topic "/slam_toolbox/feedback"
go2_ros2    | 2026-05-18 11:48:46.592 | [foxglove_bridge-21] [INFO] [1779079726.591412225] [foxglove_bridge]: Advertising new channel 19 for topic "/sim_cmd"
go2_ros2    | 2026-05-18 11:48:46.592 | [foxglove_bridge-21] [INFO] [1779079726.591804620] [foxglove_bridge]: Advertising new channel 20 for topic "/speed_limit"
go2_ros2    | 2026-05-18 11:48:46.593 | [lifecycle_manager-33] [INFO] [1779079726.591626648] [lifecycle_manager_navigation]: Configuring planner_server
ollama      | 2026-05-18 11:48:46.595 | [GIN] 2026/05/18 - 04:48:46 | 200 |      45.365µs |       127.0.0.1 | HEAD     "/"
ollama      | 2026-05-18 11:48:46.595 | [GIN] 2026/05/18 - 04:48:46 | 200 |     491.989µs |       127.0.0.1 | GET      "/api/tags"
go2_ros2    | 2026-05-18 11:48:46.595 | [planner_server-25] [INFO] [1779079726.592322769] [planner_server]: Configuring
go2_ros2    | 2026-05-18 11:48:46.595 | [planner_server-25] [INFO] [1779079726.592397741] [global_costmap.global_costmap]: Configuring
go2_ros2    | 2026-05-18 11:48:46.595 | [foxglove_bridge-21] [INFO] [1779079726.592934110] [foxglove_bridge]: Advertising new channel 21 for topic "/odom"
go2_ros2    | 2026-05-18 11:48:46.595 | [foxglove_bridge-21] [INFO] [1779079726.594548753] [foxglove_bridge]: Advertising new channel 22 for topic "/marker"
go2_ros2    | 2026-05-18 11:48:46.595 | [foxglove_bridge-21] [INFO] [1779079726.595125061] [foxglove_bridge]: Advertising new channel 23 for topic "/map"
go2_ros2    | 2026-05-18 11:48:46.595 | [foxglove_bridge-21] [INFO] [1779079726.595168050] [foxglove_bridge]: Advertising new channel 24 for topic "/route_server/transition_event"
go2_ros2    | 2026-05-18 11:48:46.595 | [foxglove_bridge-21] [INFO] [1779079726.595179188] [foxglove_bridge]: Advertising new channel 25 for topic "/local_plan"
go2_ros2    | 2026-05-18 11:48:46.596 | [foxglove_bridge-21] [INFO] [1779079726.595674535] [foxglove_bridge]: Advertising new channel 26 for topic "/local_costmap/voxel_layer_updates"
go2_ros2    | 2026-05-18 11:48:46.596 | [foxglove_bridge-21] [INFO] [1779079726.595716197] [foxglove_bridge]: Advertising new channel 27 for topic "/waypoint_follower/transition_event"
go2_ros2    | 2026-05-18 11:48:46.596 | [foxglove_bridge-21] [INFO] [1779079726.595988620] [foxglove_bridge]: Advertising new channel 28 for topic "/local_costmap/voxel_layer_raw_updates"
go2_ros2    | 2026-05-18 11:48:46.597 | [foxglove_bridge-21] [INFO] [1779079726.596869240] [foxglove_bridge]: Advertising new channel 29 for topic "/local_costmap/voxel_layer_raw"
go2_ros2    | 2026-05-18 11:48:46.598 | [foxglove_bridge-21] [INFO] [1779079726.596917428] [foxglove_bridge]: Advertising new channel 30 for topic "/local_costmap/voxel_layer"
go2_ros2    | 2026-05-18 11:48:46.598 | [foxglove_bridge-21] [INFO] [1779079726.596929668] [foxglove_bridge]: Advertising new channel 31 for topic "/local_costmap/static_layer_updates"
go2_ros2    | 2026-05-18 11:48:46.598 | [foxglove_bridge-21] [INFO] [1779079726.596938394] [foxglove_bridge]: Advertising new channel 32 for topic "/local_costmap/static_layer_raw"
go2_ros2    | 2026-05-18 11:48:46.598 | [foxglove_bridge-21] [INFO] [1779079726.598051204] [foxglove_bridge]: Advertising new channel 33 for topic "/local_costmap/published_footprint"
go2_ros2    | 2026-05-18 11:48:46.598 | [foxglove_bridge-21] [INFO] [1779079726.598103148] [foxglove_bridge]: Advertising new channel 34 for topic "/local_costmap/local_costmap/transition_event"
go2_ros2    | 2026-05-18 11:48:46.599 | [foxglove_bridge-21] [INFO] [1779079726.598128884] [foxglove_bridge]: Advertising new channel 35 for topic "/local_costmap/costmap_updates"
go2_ros2    | 2026-05-18 11:48:46.599 | [foxglove_bridge-21] [INFO] [1779079726.598139325] [foxglove_bridge]: Advertising new channel 36 for topic "/local_costmap/costmap_raw_updates"
go2_ros2    | 2026-05-18 11:48:46.599 | [foxglove_bridge-21] [INFO] [1779079726.598193194] [foxglove_bridge]: Advertising new channel 37 for topic "/local_costmap/costmap_raw"
go2_ros2    | 2026-05-18 11:48:46.599 | [foxglove_bridge-21] [INFO] [1779079726.598203039] [foxglove_bridge]: Advertising new channel 38 for topic "/local_costmap/costmap"
go2_ros2    | 2026-05-18 11:48:46.599 | [foxglove_bridge-21] [INFO] [1779079726.598622356] [foxglove_bridge]: Advertising new channel 39 for topic "/joy"
go2_ros2    | 2026-05-18 11:48:46.601 | [foxglove_bridge-21] [INFO] [1779079726.598909724] [foxglove_bridge]: Advertising new channel 40 for topic "/imu"
go2_ros2    | 2026-05-18 11:48:46.601 | [foxglove_bridge-21] [INFO] [1779079726.599263311] [foxglove_bridge]: Advertising new channel 41 for topic "/slam_toolbox/scan_visualization"
go2_ros2    | 2026-05-18 11:48:46.601 | [foxglove_bridge-21] [INFO] [1779079726.599293941] [foxglove_bridge]: Advertising new channel 42 for topic "/local_costmap/static_layer"
go2_ros2    | 2026-05-18 11:48:46.601 | [foxglove_bridge-21] [INFO] [1779079726.599956586] [foxglove_bridge]: Advertising new channel 43 for topic "/local_costmap/clearing_endpoints"
go2_ros2    | 2026-05-18 11:48:46.601 | [foxglove_bridge-21] [INFO] [1779079726.601036506] [foxglove_bridge]: Advertising new channel 44 for topic "/go2_camera/color/camera_info"
go2_ros2    | 2026-05-18 11:48:46.601 | [foxglove_bridge-21] [INFO] [1779079726.601090494] [foxglove_bridge]: Advertising new channel 45 for topic "/go2/scan"
go2_ros2    | 2026-05-18 11:48:46.602 | [foxglove_bridge-21] [INFO] [1779079726.601369883] [foxglove_bridge]: Advertising new channel 46 for topic "/go2/robot_velocity"
go2_ros2    | 2026-05-18 11:48:46.602 | [foxglove_bridge-21] [INFO] [1779079726.601410643] [foxglove_bridge]: Advertising new channel 47 for topic "/velocity_smoother/transition_event"
go2_ros2    | 2026-05-18 11:48:46.602 | [foxglove_bridge-21] [INFO] [1779079726.601599812] [foxglove_bridge]: Advertising new channel 48 for topic "/go2/robot_mode"
go2_ros2    | 2026-05-18 11:48:46.605 | [foxglove_bridge-21] [INFO] [1779079726.604462389] [foxglove_bridge]: Advertising new channel 49 for topic "/slam_toolbox/update"
go2_ros2    | 2026-05-18 11:48:46.606 | [foxglove_bridge-21] [INFO] [1779079726.605078723] [foxglove_bridge]: Advertising new channel 50 for topic "/go2/foot_contact"
go2_ros2    | 2026-05-18 11:48:46.606 | [foxglove_bridge-21] [INFO] [1779079726.605869600] [foxglove_bridge]: Advertising new channel 51 for topic "/pose"
go2_ros2    | 2026-05-18 11:48:46.606 | [foxglove_bridge-21] [INFO] [1779079726.605998748] [foxglove_bridge]: Advertising new channel 52 for topic "/local_costmap/static_layer_raw_updates"
go2_ros2    | 2026-05-18 11:48:46.607 | [foxglove_bridge-21] [INFO] [1779079726.606578504] [foxglove_bridge]: Advertising new channel 53 for topic "/go2/controller_velocity"
go2_ros2    | 2026-05-18 11:48:46.607 | [foxglove_bridge-21] [INFO] [1779079726.606622271] [foxglove_bridge]: Advertising new channel 54 for topic "/global_costmap/published_footprint"
go2_ros2    | 2026-05-18 11:48:46.607 | [foxglove_bridge-21] [INFO] [1779079726.606634785] [foxglove_bridge]: Advertising new channel 55 for topic "/global_costmap/global_costmap/transition_event"
go2_ros2    | 2026-05-18 11:48:46.607 | [foxglove_bridge-21] [INFO] [1779079726.606643613] [foxglove_bridge]: Advertising new channel 56 for topic "/global_costmap/costmap_raw_updates"
go2_ros2    | 2026-05-18 11:48:46.608 | [foxglove_bridge-21] [INFO] [1779079726.606660271] [foxglove_bridge]: Advertising new channel 57 for topic "/scan"
go2_ros2    | 2026-05-18 11:48:46.608 | [foxglove_bridge-21] [INFO] [1779079726.606987888] [foxglove_bridge]: Advertising new channel 58 for topic "/local_costmap/voxel_grid"
go2_ros2    | 2026-05-18 11:48:46.608 | [foxglove_bridge-21] [INFO] [1779079726.607205531] [foxglove_bridge]: Advertising new channel 59 for topic "/local_costmap/footprint"
go2_ros2    | 2026-05-18 11:48:46.608 | [foxglove_bridge-21] [INFO] [1779079726.607228108] [foxglove_bridge]: Advertising new channel 60 for topic "/global_costmap/costmap_raw"
go2_ros2    | 2026-05-18 11:48:46.608 | [foxglove_bridge-21] [INFO] [1779079726.607240100] [foxglove_bridge]: Advertising new channel 61 for topic "/foot_markers"
go2_ros2    | 2026-05-18 11:48:46.610 | [foxglove_bridge-21] [INFO] [1779079726.609380664] [foxglove_bridge]: Advertising new channel 62 for topic "/evaluation"
go2_ros2    | 2026-05-18 11:48:46.610 | [foxglove_bridge-21] [INFO] [1779079726.609671609] [foxglove_bridge]: Advertising new channel 63 for topic "/docking_server/transition_event"
go2_ros2    | 2026-05-18 11:48:46.611 | [foxglove_bridge-21] [INFO] [1779079726.610459138] [foxglove_bridge]: Advertising new channel 64 for topic "/go2/joint_group_controller/commands"
go2_ros2    | 2026-05-18 11:48:46.611 | [foxglove_bridge-21] [INFO] [1779079726.610516539] [foxglove_bridge]: Advertising new channel 65 for topic "/cost_cloud"
go2_ros2    | 2026-05-18 11:48:46.611 | [foxglove_bridge-21] [INFO] [1779079726.610537961] [foxglove_bridge]: Advertising new channel 66 for topic "/controller_server/transition_event"
go2_ros2    | 2026-05-18 11:48:46.611 | [foxglove_bridge-21] [INFO] [1779079726.610547835] [foxglove_bridge]: Advertising new channel 67 for topic "/plan_smoothed"
go2_ros2    | 2026-05-18 11:48:46.611 | [foxglove_bridge-21] [INFO] [1779079726.610560448] [foxglove_bridge]: Advertising new channel 68 for topic "/collision_monitor/transition_event"
go2_ros2    | 2026-05-18 11:48:46.611 | [foxglove_bridge-21] [INFO] [1779079726.610567797] [foxglove_bridge]: Advertising new channel 69 for topic "/cmd_vel_voice"
go2_ros2    | 2026-05-18 11:48:46.611 | [foxglove_bridge-21] [INFO] [1779079726.610574334] [foxglove_bridge]: Advertising new channel 70 for topic "/cmd_vel_out"
go2_ros2    | 2026-05-18 11:48:46.611 | [foxglove_bridge-21] [INFO] [1779079726.610581790] [foxglove_bridge]: Advertising new channel 71 for topic "/received_global_plan"
go2_ros2    | 2026-05-18 11:48:46.611 | [foxglove_bridge-21] [INFO] [1779079726.610589065] [foxglove_bridge]: Advertising new channel 72 for topic "/cmd_vel_nav"
go2_ros2    | 2026-05-18 11:48:46.612 | [foxglove_bridge-21] [INFO] [1779079726.610933284] [foxglove_bridge]: Advertising new channel 73 for topic "/map_metadata"
go2_ros2    | 2026-05-18 11:48:46.612 | [foxglove_bridge-21] [INFO] [1779079726.610997821] [foxglove_bridge]: Advertising new channel 74 for topic "/cmd_vel_joy"
go2_ros2    | 2026-05-18 11:48:46.612 | [foxglove_bridge-21] [INFO] [1779079726.611009203] [foxglove_bridge]: Advertising new channel 75 for topic "/cmd_vel_foxglove"
go2_ros2    | 2026-05-18 11:48:46.612 | [foxglove_bridge-21] [INFO] [1779079726.611337403] [foxglove_bridge]: Advertising new channel 76 for topic "/slam_toolbox/graph_visualization"
go2_ros2    | 2026-05-18 11:48:46.612 | [foxglove_bridge-21] [INFO] [1779079726.611390690] [foxglove_bridge]: Advertising new channel 77 for topic "/cmd_vel"
go2_ros2    | 2026-05-18 11:48:46.613 | [foxglove_bridge-21] [INFO] [1779079726.611418139] [foxglove_bridge]: Advertising new channel 78 for topic "/go2/imu_plugin/out"
go2_ros2    | 2026-05-18 11:48:46.613 | [foxglove_bridge-21] [INFO] [1779079726.611433536] [foxglove_bridge]: Advertising new channel 79 for topic "/bt_navigator/transition_event"
go2_ros2    | 2026-05-18 11:48:46.614 | [foxglove_bridge-21] [INFO] [1779079726.611451740] [foxglove_bridge]: Advertising new channel 80 for topic "/go2/color/camera_info"
go2_ros2    | 2026-05-18 11:48:46.614 | [foxglove_bridge-21] [INFO] [1779079726.611465299] [foxglove_bridge]: Advertising new channel 81 for topic "/behavior_server/transition_event"
go2_ros2    | 2026-05-18 11:48:46.895 | [planner_server-25] [INFO] [1779079726.894769772] [global_costmap.global_costmap]: Using plugin "static_layer"
go2_ros2    | 2026-05-18 11:48:46.914 | [planner_server-25] [INFO] [1779079726.910846699] [global_costmap.global_costmap]: Subscribing to the map topic (/map) with transient local durability
go2_ros2    | 2026-05-18 11:48:46.928 | [planner_server-25] [INFO] [1779079726.927389276] [global_costmap.global_costmap]: Initialized plugin "static_layer"
go2_ros2    | 2026-05-18 11:48:46.941 | [planner_server-25] [INFO] [1779079726.929137307] [global_costmap.global_costmap]: Using plugin "voxel_layer"
go2_ros2    | 2026-05-18 11:48:46.942 | [planner_server-25] [INFO] [1779079726.931435601] [global_costmap.global_costmap]: Subscribed to Topics: scan
go2_ros2    | 2026-05-18 11:48:47.779 | [planner_server-25] [INFO] [1779079727.777806948] [global_costmap.global_costmap]: Initialized plugin "voxel_layer"
go2_ros2    | 2026-05-18 11:48:47.779 | [planner_server-25] [INFO] [1779079727.777896428] [global_costmap.global_costmap]: Using plugin "inflation_layer"
go2_ros2    | 2026-05-18 11:48:47.816 | [planner_server-25] [INFO] [1779079727.815098884] [global_costmap.global_costmap]: Initialized plugin "inflation_layer"
go2_ros2    | 2026-05-18 11:48:47.961 | [planner_server-25] [INFO] [1779079727.960448696] [planner_server]: Created global planner plugin GridBased of type nav2_smac_planner::SmacPlannerHybrid
go2_ros2    | 2026-05-18 11:48:47.961 | [planner_server-25] [INFO] [1779079727.960566345] [planner_server]: Configuring GridBased of type SmacPlannerHybrid
go2_ros2    | 2026-05-18 11:48:47.975 | [planner_server-25] [INFO] [1779079727.971202232] [planner_server]: Even sized heuristic lookup table size set 400.000000, increasing size by 1 to make odd
go2_ros2    | 2026-05-18 11:48:49.251 | [foxglove_bridge-21] [INFO] [1779079729.250582001] [foxglove_bridge]: Advertising new channel 82 for topic "/robot_description"
go2_ros2    | 2026-05-18 11:48:49.251 | [foxglove_bridge-21] [INFO] [1779079729.250667551] [foxglove_bridge]: Advertising new channel 83 for topic "/global_costmap/voxel_layer_updates"
go2_ros2    | 2026-05-18 11:48:49.251 | [foxglove_bridge-21] [INFO] [1779079729.250675803] [foxglove_bridge]: Advertising new channel 84 for topic "/global_costmap/voxel_layer_raw"
go2_ros2    | 2026-05-18 11:48:49.251 | [foxglove_bridge-21] [INFO] [1779079729.250681505] [foxglove_bridge]: Advertising new channel 85 for topic "/global_costmap/voxel_layer"
go2_ros2    | 2026-05-18 11:48:49.251 | [foxglove_bridge-21] [INFO] [1779079729.250686129] [foxglove_bridge]: Advertising new channel 86 for topic "/joint_states"
go2_ros2    | 2026-05-18 11:48:49.251 | [foxglove_bridge-21] [INFO] [1779079729.250690466] [foxglove_bridge]: Advertising new channel 87 for topic "/global_costmap/voxel_grid"
go2_ros2    | 2026-05-18 11:48:49.251 | [foxglove_bridge-21] [INFO] [1779079729.250695242] [foxglove_bridge]: Advertising new channel 88 for topic "/global_costmap/static_layer_updates"
go2_ros2    | 2026-05-18 11:48:49.251 | [foxglove_bridge-21] [INFO] [1779079729.250700543] [foxglove_bridge]: Advertising new channel 89 for topic "/global_costmap/static_layer_raw_updates"
go2_ros2    | 2026-05-18 11:48:49.251 | [foxglove_bridge-21] [INFO] [1779079729.250705958] [foxglove_bridge]: Advertising new channel 90 for topic "/global_costmap/static_layer_raw"
go2_ros2    | 2026-05-18 11:48:49.251 | [foxglove_bridge-21] [INFO] [1779079729.250710402] [foxglove_bridge]: Advertising new channel 91 for topic "/global_costmap/static_layer"
go2_ros2    | 2026-05-18 11:48:49.251 | [foxglove_bridge-21] [INFO] [1779079729.250715995] [foxglove_bridge]: Advertising new channel 92 for topic "/global_costmap/footprint"
go2_ros2    | 2026-05-18 11:48:49.251 | [foxglove_bridge-21] [INFO] [1779079729.250719952] [foxglove_bridge]: Advertising new channel 93 for topic "/global_costmap/costmap_updates"
go2_ros2    | 2026-05-18 11:48:49.251 | [foxglove_bridge-21] [INFO] [1779079729.250724715] [foxglove_bridge]: Advertising new channel 94 for topic "/global_costmap/costmap"
go2_ros2    | 2026-05-18 11:48:49.251 | [foxglove_bridge-21] [INFO] [1779079729.250729194] [foxglove_bridge]: Advertising new channel 95 for topic "/global_costmap/clearing_endpoints"
go2_ros2    | 2026-05-18 11:48:49.251 | [foxglove_bridge-21] [INFO] [1779079729.250733845] [foxglove_bridge]: Advertising new channel 96 for topic "/global_costmap/voxel_layer_raw_updates"
go2_ros2    | 2026-05-18 11:48:52.697 | [gazebo-1] Escalating to SIGKILL on [Gazebo Sim Server]
go2_ros2    | 2026-05-18 11:48:52.702 | [INFO] [gazebo-1]: process has finished cleanly [pid 70]
go2_ros2    | 2026-05-18 11:48:52.703 | [INFO] [launch]: process[gazebo-1] was required: shutting down launched system
go2_ros2    | 2026-05-18 11:48:52.934 | [INFO] [voice_cmd_node-35]: sending signal 'SIGINT' to process[voice_cmd_node-35]
go2_ros2    | 2026-05-18 11:48:52.940 | [INFO] [mic_bridge_node-34]: sending signal 'SIGINT' to process[mic_bridge_node-34]
go2_ros2    | 2026-05-18 11:48:52.959 | [INFO] [lifecycle_manager-33]: sending signal 'SIGINT' to process[lifecycle_manager-33]
go2_ros2    | 2026-05-18 11:48:52.970 | [INFO] [opennav_docking-32]: sending signal 'SIGINT' to process[opennav_docking-32]
go2_ros2    | 2026-05-18 11:48:52.978 | [INFO] [collision_monitor-31]: sending signal 'SIGINT' to process[collision_monitor-31]
go2_ros2    | 2026-05-18 11:48:52.991 | [INFO] [velocity_smoother-30]: sending signal 'SIGINT' to process[velocity_smoother-30]
go2_ros2    | 2026-05-18 11:48:53.017 | [INFO] [waypoint_follower-29]: sending signal 'SIGINT' to process[waypoint_follower-29]
go2_ros2    | 2026-05-18 11:48:53.046 | [INFO] [bt_navigator-28]: sending signal 'SIGINT' to process[bt_navigator-28]
go2_ros2    | 2026-05-18 11:48:53.055 | [INFO] [behavior_server-27]: sending signal 'SIGINT' to process[behavior_server-27]
go2_ros2    | 2026-05-18 11:48:53.082 | [INFO] [route_server-26]: sending signal 'SIGINT' to process[route_server-26]
go2_ros2    | 2026-05-18 11:48:53.110 | [INFO] [planner_server-25]: sending signal 'SIGINT' to process[planner_server-25]
go2_ros2    | 2026-05-18 11:48:53.123 | [INFO] [smoother_server-24]: sending signal 'SIGINT' to process[smoother_server-24]
go2_ros2    | 2026-05-18 11:48:53.144 | [INFO] [controller_server-23]: sending signal 'SIGINT' to process[controller_server-23]
go2_ros2    | 2026-05-18 11:48:53.176 | [INFO] [async_slam_toolbox_node-22]: sending signal 'SIGINT' to process[async_slam_toolbox_node-22]
go2_ros2    | 2026-05-18 11:48:53.184 | [INFO] [foxglove_bridge-21]: sending signal 'SIGINT' to process[foxglove_bridge-21]
go2_ros2    | 2026-05-18 11:48:53.205 | [INFO] [twist_mux-19]: sending signal 'SIGINT' to process[twist_mux-19]
go2_ros2    | 2026-05-18 11:48:53.243 | [INFO] [teleop_node-18]: sending signal 'SIGINT' to process[teleop_node-18]
go2_ros2    | 2026-05-18 11:48:53.268 | [INFO] [joy_node-17]: sending signal 'SIGINT' to process[joy_node-17]
go2_ros2    | 2026-05-18 11:48:53.284 | [INFO] [sim_cmd_node.py-16]: sending signal 'SIGINT' to process[sim_cmd_node.py-16]
go2_ros2    | 2026-05-18 11:48:53.319 | [INFO] [relay-15]: sending signal 'SIGINT' to process[relay-15]
go2_ros2    | 2026-05-18 11:48:53.339 | [INFO] [opennav_docking-32]: process has finished cleanly [pid 251]
go2_ros2    | 2026-05-18 11:48:53.339 | [INFO] [collision_monitor-31]: process has finished cleanly [pid 245]
go2_ros2    | 2026-05-18 11:48:53.376 | [INFO] [relay-14]: sending signal 'SIGINT' to process[relay-14]
go2_ros2    | 2026-05-18 11:48:53.394 | [INFO] [velocity_smoother-30]: process has finished cleanly [pid 234]
go2_ros2    | 2026-05-18 11:48:53.413 | [INFO] [relay-13]: sending signal 'SIGINT' to process[relay-13]
go2_ros2    | 2026-05-18 11:48:53.418 | [INFO] [waypoint_follower-29]: process has finished cleanly [pid 198]
go2_ros2    | 2026-05-18 11:48:53.443 | [INFO] [relay-12]: sending signal 'SIGINT' to process[relay-12]
go2_ros2    | 2026-05-18 11:48:53.463 | [INFO] [bt_navigator-28]: process has finished cleanly [pid 179]
go2_ros2    | 2026-05-18 11:48:53.470 | [INFO] [behavior_server-27]: process has finished cleanly [pid 164]
go2_ros2    | 2026-05-18 11:48:53.514 | [INFO] [relay-11]: sending signal 'SIGINT' to process[relay-11]
go2_ros2    | 2026-05-18 11:48:53.519 | [ERROR] [voice_cmd_node-35]: process has died [pid 297, exit code 1, cmd '/ros2_ws/install/speech_processor/lib/speech_processor/voice_cmd_node --ros-args -r __node:=voice_cmd_node --params-file /tmp/launch_params_z9rx195z'].
go2_ros2    | 2026-05-18 11:48:53.553 | [INFO] [QuadrupedOdometryNode.py-10]: sending signal 'SIGINT' to process[QuadrupedOdometryNode.py-10]
go2_ros2    | 2026-05-18 11:48:53.558 | [INFO] [route_server-26]: process has finished cleanly [pid 126]
go2_ros2    | 2026-05-18 11:48:53.593 | [INFO] [robot_controller_gazebo.py-9]: sending signal 'SIGINT' to process[robot_controller_gazebo.py-9]
go2_ros2    | 2026-05-18 11:48:53.609 | [INFO] [twist_mux-19]: process has finished cleanly [pid 91]
go2_ros2    | 2026-05-18 11:48:53.609 | [INFO] [teleop_node-18]: process has finished cleanly [pid 90]
go2_ros2    | 2026-05-18 11:48:53.629 | [INFO] [cmd_vel_pub.py-8]: sending signal 'SIGINT' to process[cmd_vel_pub.py-8]
go2_ros2    | 2026-05-18 11:48:53.643 | [ERROR] [mic_bridge_node-34]: process has died [pid 279, exit code 1, cmd '/ros2_ws/install/speech_processor/lib/speech_processor/mic_bridge_node --ros-args -r __node:=mic_bridge_node --params-file /tmp/launch_params_ebj5higv'].
go2_ros2    | 2026-05-18 11:48:53.647 | [INFO] [smoother_server-24]: process has finished cleanly [pid 108]
go2_ros2    | 2026-05-18 11:48:53.676 | [INFO] [image_bridge-7]: sending signal 'SIGINT' to process[image_bridge-7]
go2_ros2    | 2026-05-18 11:48:53.724 | [INFO] [parameter_bridge-6]: sending signal 'SIGINT' to process[parameter_bridge-6]
go2_ros2    | 2026-05-18 11:48:53.730 | [INFO] [relay-15]: process has finished cleanly [pid 85]
go2_ros2    | 2026-05-18 11:48:53.730 | [INFO] [relay-14]: process has finished cleanly [pid 84]
go2_ros2    | 2026-05-18 11:48:53.740 | [INFO] [joy_node-17]: process has finished cleanly [pid 89]
go2_ros2    | 2026-05-18 11:48:53.741 | [INFO] [relay-13]: process has finished cleanly [pid 83]
go2_ros2    | 2026-05-18 11:48:53.763 | [INFO] [parameter_bridge-5]: sending signal 'SIGINT' to process[parameter_bridge-5]
go2_ros2    | 2026-05-18 11:48:53.765 | [INFO] [relay-12]: process has finished cleanly [pid 82]
go2_ros2    | 2026-05-18 11:48:53.791 | [INFO] [robot_state_publisher-3]: sending signal 'SIGINT' to process[robot_state_publisher-3]
go2_ros2    | 2026-05-18 11:48:53.793 | [INFO] [relay-11]: process has finished cleanly [pid 81]
go2_ros2    | 2026-05-18 11:48:53.793 | [INFO] [async_slam_toolbox_node-22]: process has finished cleanly [pid 100]
go2_ros2    | 2026-05-18 11:48:53.825 | [INFO] [robot_state_publisher-2]: sending signal 'SIGINT' to process[robot_state_publisher-2]
go2_ros2    | 2026-05-18 11:48:53.827 | [lifecycle_manager-33] [INFO] [1779079732.959506836] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:48:53.827 | [lifecycle_manager-33] [INFO] [1779079732.960134243] [lifecycle_manager_navigation]: Running Nav2 LifecycleManager rcl preshutdown (lifecycle_manager_navigation)
go2_ros2    | 2026-05-18 11:48:53.829 | [opennav_docking-32] [INFO] [1779079732.971165009] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:48:53.829 | [opennav_docking-32] [INFO] [1779079732.972129302] [docking_server]: Running Nav2 LifecycleNode rcl preshutdown (docking_server)
go2_ros2    | 2026-05-18 11:48:53.829 | [opennav_docking-32] [INFO] [1779079732.972208827] [docking_server]: Destroying bond (docking_server) to lifecycle manager.
go2_ros2    | 2026-05-18 11:48:53.831 | [opennav_docking-32] [INFO] [1779079732.979205306] [docking_server]: Destroying
go2_ros2    | 2026-05-18 11:48:53.832 | [collision_monitor-31] [INFO] [1779079732.981132866] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:48:53.832 | [collision_monitor-31] [INFO] [1779079732.981508199] [collision_monitor]: Running Nav2 LifecycleNode rcl preshutdown (collision_monitor)
go2_ros2    | 2026-05-18 11:48:53.832 | [collision_monitor-31] [INFO] [1779079732.981649717] [collision_monitor]: Destroying bond (collision_monitor) to lifecycle manager.
go2_ros2    | 2026-05-18 11:48:53.833 | [collision_monitor-31] [INFO] [1779079732.983820025] [collision_monitor]: Destroying
go2_ros2    | 2026-05-18 11:48:53.840 | [velocity_smoother-30] [INFO] [1779079732.991867899] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:48:53.841 | [velocity_smoother-30] [INFO] [1779079732.991993182] [velocity_smoother]: Running Nav2 LifecycleNode rcl preshutdown (velocity_smoother)
go2_ros2    | 2026-05-18 11:48:53.841 | [velocity_smoother-30] [INFO] [1779079732.992039096] [velocity_smoother]: Destroying bond (velocity_smoother) to lifecycle manager.
go2_ros2    | 2026-05-18 11:48:53.842 | [velocity_smoother-30] [INFO] [1779079732.997917237] [velocity_smoother]: Destroying
go2_ros2    | 2026-05-18 11:48:53.842 | [ERROR] [sim_cmd_node.py-16]: process has died [pid 88, exit code 1, cmd '/ros2_ws/install/go2_sim/lib/go2_sim/sim_cmd_node.py --ros-args -r __node:=sim_cmd_node --params-file /tmp/launch_params_5fwyjz1t'].
go2_ros2    | 2026-05-18 11:48:53.846 | [voice_cmd_node-35] Traceback (most recent call last):
go2_ros2    | 2026-05-18 11:48:53.846 | [voice_cmd_node-35]   File "/ros2_ws/install/speech_processor/lib/speech_processor/voice_cmd_node", line 33, in <module>
go2_ros2    | 2026-05-18 11:48:53.850 | [voice_cmd_node-35]     sys.exit(load_entry_point('speech-processor==1.0.0', 'console_scripts', 'voice_cmd_node')())
go2_ros2    | 2026-05-18 11:48:53.855 | [voice_cmd_node-35]              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
go2_ros2    | 2026-05-18 11:48:53.855 | [voice_cmd_node-35]   File "/ros2_ws/install/speech_processor/lib/python3.12/site-packages/speech_processor/voice_cmd_node.py", line 501, in main
go2_ros2    | 2026-05-18 11:48:53.855 | [voice_cmd_node-35]     rclpy.shutdown()
go2_ros2    | 2026-05-18 11:48:53.855 | [voice_cmd_node-35]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/__init__.py", line 134, in shutdown
go2_ros2    | 2026-05-18 11:48:53.855 | [voice_cmd_node-35]     _shutdown(context=context)
go2_ros2    | 2026-05-18 11:48:53.856 | [voice_cmd_node-35]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/utilities.py", line 82, in shutdown
go2_ros2    | 2026-05-18 11:48:53.856 | [voice_cmd_node-35]     context.shutdown()
go2_ros2    | 2026-05-18 11:48:53.856 | [voice_cmd_node-35]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/context.py", line 129, in shutdown
go2_ros2    | 2026-05-18 11:48:53.856 | [voice_cmd_node-35]     self.__context.shutdown()
go2_ros2    | 2026-05-18 11:48:53.856 | [voice_cmd_node-35] rclpy._rclpy_pybind11.RCLError: failed to shutdown: rcl_shutdown already called on the given context, at ./src/rcl/init.c:333
go2_ros2    | 2026-05-18 11:48:53.857 | [waypoint_follower-29] [INFO] [1779079733.018286592] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:48:53.857 | [waypoint_follower-29] [INFO] [1779079733.018523460] [waypoint_follower]: Running Nav2 LifecycleNode rcl preshutdown (waypoint_follower)
go2_ros2    | 2026-05-18 11:48:53.857 | [waypoint_follower-29] [INFO] [1779079733.018815787] [waypoint_follower]: Destroying bond (waypoint_follower) to lifecycle manager.
go2_ros2    | 2026-05-18 11:48:53.857 | [waypoint_follower-29] [INFO] [1779079733.026368104] [waypoint_follower]: Destroying
go2_ros2    | 2026-05-18 11:48:53.857 | [bt_navigator-28] [INFO] [1779079733.047731250] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:48:53.857 | [bt_navigator-28] [INFO] [1779079733.048884122] [bt_navigator]: Running Nav2 LifecycleNode rcl preshutdown (bt_navigator)
go2_ros2    | 2026-05-18 11:48:53.857 | [bt_navigator-28] [INFO] [1779079733.049056643] [bt_navigator]: Destroying bond (bt_navigator) to lifecycle manager.
go2_ros2    | 2026-05-18 11:48:53.859 | [mic_bridge_node-34] Traceback (most recent call last):
go2_ros2    | 2026-05-18 11:48:53.860 | [mic_bridge_node-34]   File "/ros2_ws/install/speech_processor/lib/speech_processor/mic_bridge_node", line 33, in <module>
go2_ros2    | 2026-05-18 11:48:53.861 | [mic_bridge_node-34]     sys.exit(load_entry_point('speech-processor==1.0.0', 'console_scripts', 'mic_bridge_node')())
go2_ros2    | 2026-05-18 11:48:53.861 | [mic_bridge_node-34]              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
go2_ros2    | 2026-05-18 11:48:53.862 | [mic_bridge_node-34]   File "/ros2_ws/install/speech_processor/lib/python3.12/site-packages/speech_processor/mic_bridge_node.py", line 522, in main
go2_ros2    | 2026-05-18 11:48:53.862 | [mic_bridge_node-34]     rclpy.shutdown()
go2_ros2    | 2026-05-18 11:48:53.863 | [mic_bridge_node-34]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/__init__.py", line 134, in shutdown
go2_ros2    | 2026-05-18 11:48:53.863 | [mic_bridge_node-34]     _shutdown(context=context)
go2_ros2    | 2026-05-18 11:48:53.866 | [mic_bridge_node-34]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/utilities.py", line 82, in shutdown
go2_ros2    | 2026-05-18 11:48:53.866 | [mic_bridge_node-34]     context.shutdown()
go2_ros2    | 2026-05-18 11:48:53.867 | [mic_bridge_node-34]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/context.py", line 129, in shutdown
go2_ros2    | 2026-05-18 11:48:53.871 | [mic_bridge_node-34]     self.__context.shutdown()
go2_ros2    | 2026-05-18 11:48:53.871 | [mic_bridge_node-34] rclpy._rclpy_pybind11.RCLError: failed to shutdown: rcl_shutdown already called on the given context, at ./src/rcl/init.c:333
go2_ros2    | 2026-05-18 11:48:53.874 | [bt_navigator-28] [INFO] [1779079733.057655901] [bt_navigator]: Destroying
go2_ros2    | 2026-05-18 11:48:53.874 | [behavior_server-27] [INFO] [1779079733.060794150] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:48:53.875 | [behavior_server-27] [INFO] [1779079733.060976428] [behavior_server]: Running Nav2 LifecycleNode rcl preshutdown (behavior_server)
go2_ros2    | 2026-05-18 11:48:53.875 | [behavior_server-27] [INFO] [1779079733.061024471] [behavior_server]: Destroying bond (behavior_server) to lifecycle manager.
go2_ros2    | 2026-05-18 11:48:53.875 | [behavior_server-27] [INFO] [1779079733.080162010] [behavior_server]: Destroying
go2_ros2    | 2026-05-18 11:48:53.875 | [route_server-26] [INFO] [1779079733.082313703] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:48:53.875 | [route_server-26] [INFO] [1779079733.082493504] [route_server]: Running Nav2 LifecycleNode rcl preshutdown (route_server)
go2_ros2    | 2026-05-18 11:48:53.875 | [route_server-26] [INFO] [1779079733.082549180] [route_server]: Destroying bond (route_server) to lifecycle manager.
go2_ros2    | 2026-05-18 11:48:53.875 | [route_server-26] [INFO] [1779079733.099093072] [route_server]: Destroying
go2_ros2    | 2026-05-18 11:48:53.875 | [planner_server-25] [INFO] [1779079733.110389726] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:48:53.875 | [planner_server-25] [INFO] [1779079733.110671176] [planner_server]: Running Nav2 LifecycleNode rcl preshutdown (planner_server)
go2_ros2    | 2026-05-18 11:48:53.875 | [planner_server-25] [INFO] [1779079733.110726739] [planner_server]: Destroying bond (planner_server) to lifecycle manager.
go2_ros2    | 2026-05-18 11:48:53.876 | [smoother_server-24] [INFO] [1779079733.123442647] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:48:53.876 | [smoother_server-24] [INFO] [1779079733.123764360] [smoother_server]: Running Nav2 LifecycleNode rcl preshutdown (smoother_server)
go2_ros2    | 2026-05-18 11:48:53.877 | [smoother_server-24] [INFO] [1779079733.123856533] [smoother_server]: Cleaning up
go2_ros2    | 2026-05-18 11:48:53.877 | [controller_server-23] [INFO] [1779079733.144718719] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:48:53.877 | [controller_server-23] [INFO] [1779079733.144847918] [controller_server]: Running Nav2 LifecycleNode rcl preshutdown (controller_server)
go2_ros2    | 2026-05-18 11:48:53.877 | [controller_server-23] [INFO] [1779079733.145002639] [controller_server]: Cleaning up
go2_ros2    | 2026-05-18 11:48:53.877 | [controller_server-23] [INFO] [1779079733.146439016] [local_costmap.local_costmap]: Cleaning up
go2_ros2    | 2026-05-18 11:48:53.877 | [async_slam_toolbox_node-22] [INFO] [1779079733.176894151] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:48:53.878 | [foxglove_bridge-21] [INFO] [1779079733.185125749] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:48:53.878 | [twist_mux-19] [INFO] [1779079733.204569685] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:48:53.878 | [foxglove_bridge-21] [INFO] [1779079733.217718233] [foxglove_bridge]: Shutting down foxglove_bridge
go2_ros2    | 2026-05-18 11:48:53.878 | [smoother_server-24] [INFO] [1779079733.239300202] [smoother_server]: Destroying bond (smoother_server) to lifecycle manager.
go2_ros2    | 2026-05-18 11:48:53.879 | [teleop_node-18] [INFO] [1779079733.244111093] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:48:53.880 | [smoother_server-24] [INFO] [1779079733.264372692] [smoother_server]: Destroying
go2_ros2    | 2026-05-18 11:48:53.882 | [joy_node-17] [INFO] [1779079733.274476933] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:48:53.893 | [relay-15] [INFO] [1779079733.321207131] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:48:53.895 | [relay-14] [INFO] [1779079733.381183777] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:48:53.897 | [foxglove_bridge-21] [INFO] [1779079733.406274443] [foxglove_bridge]: Shutdown complete
go2_ros2    | 2026-05-18 11:48:53.897 | [relay-13] [INFO] [1779079733.413744323] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:48:53.903 | [relay-12] [INFO] [1779079733.444147465] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:48:53.903 | [sim_cmd_node.py-16] Traceback (most recent call last):
go2_ros2    | 2026-05-18 11:48:53.903 | [sim_cmd_node.py-16]   File "/ros2_ws/install/go2_sim/lib/go2_sim/sim_cmd_node.py", line 185, in <module>
go2_ros2    | 2026-05-18 11:48:53.903 | [sim_cmd_node.py-16]     main()
go2_ros2    | 2026-05-18 11:48:53.904 | [sim_cmd_node.py-16]   File "/ros2_ws/install/go2_sim/lib/go2_sim/sim_cmd_node.py", line 181, in main
go2_ros2    | 2026-05-18 11:48:53.904 | [sim_cmd_node.py-16]     rclpy.shutdown()
go2_ros2    | 2026-05-18 11:48:53.904 | [sim_cmd_node.py-16]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/__init__.py", line 134, in shutdown
go2_ros2    | 2026-05-18 11:48:53.904 | [sim_cmd_node.py-16]     _shutdown(context=context)
go2_ros2    | 2026-05-18 11:48:53.904 | [sim_cmd_node.py-16]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/utilities.py", line 82, in shutdown
go2_ros2    | 2026-05-18 11:48:53.904 | [sim_cmd_node.py-16]     context.shutdown()
go2_ros2    | 2026-05-18 11:48:53.904 | [sim_cmd_node.py-16]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/context.py", line 129, in shutdown
go2_ros2    | 2026-05-18 11:48:53.904 | [sim_cmd_node.py-16]     self.__context.shutdown()
go2_ros2    | 2026-05-18 11:48:53.904 | [sim_cmd_node.py-16] rclpy._rclpy_pybind11.RCLError: failed to shutdown: rcl_shutdown already called on the given context, at ./src/rcl/init.c:333
go2_ros2    | 2026-05-18 11:48:53.904 | [INFO] [controller_server-23]: process has finished cleanly [pid 101]
go2_ros2    | 2026-05-18 11:48:53.906 | [controller_server-23] [INFO] [1779079733.494442166] [controller_server]: Destroying bond (controller_server) to lifecycle manager.
go2_ros2    | 2026-05-18 11:48:53.920 | [relay-11] [INFO] [1779079733.515176187] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:48:53.926 | [INFO] [parameter_bridge-6]: process has finished cleanly [pid 76]
go2_ros2    | 2026-05-18 11:48:53.927 | [INFO] [image_bridge-7]: process has finished cleanly [pid 77]
go2_ros2    | 2026-05-18 11:48:53.928 | [INFO] [parameter_bridge-5]: process has finished cleanly [pid 75]
go2_ros2    | 2026-05-18 11:48:53.942 | [controller_server-23] [INFO] [1779079733.566938603] [local_costmap.local_costmap]: Destroying
go2_ros2    | 2026-05-18 11:48:53.942 | [robot_controller_gazebo.py-9] Traceback (most recent call last):
go2_ros2    | 2026-05-18 11:48:53.942 | [robot_controller_gazebo.py-9]   File "/ros2_ws/install/go2_sim/lib/go2_sim/robot_controller_gazebo.py", line 77, in <module>
go2_ros2    | 2026-05-18 11:48:53.942 | [robot_controller_gazebo.py-9]     main()
go2_ros2    | 2026-05-18 11:48:53.942 | [robot_controller_gazebo.py-9]   File "/ros2_ws/install/go2_sim/lib/go2_sim/robot_controller_gazebo.py", line 72, in main
go2_ros2    | 2026-05-18 11:48:53.942 | [robot_controller_gazebo.py-9]     rclpy.spin(node)
go2_ros2    | 2026-05-18 11:48:53.950 | [robot_controller_gazebo.py-9]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/__init__.py", line 247, in spin
go2_ros2    | 2026-05-18 11:48:53.950 | [robot_controller_gazebo.py-9]     executor.spin_once()
go2_ros2    | 2026-05-18 11:48:53.950 | [robot_controller_gazebo.py-9]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/executors.py", line 926, in spin_once
go2_ros2    | 2026-05-18 11:48:53.950 | [robot_controller_gazebo.py-9]     self._spin_once_impl(timeout_sec)
go2_ros2    | 2026-05-18 11:48:53.950 | [robot_controller_gazebo.py-9]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/executors.py", line 907, in _spin_once_impl
go2_ros2    | 2026-05-18 11:48:53.950 | [robot_controller_gazebo.py-9]     handler, entity, node = self.wait_for_ready_callbacks(
go2_ros2    | 2026-05-18 11:48:53.950 | [robot_controller_gazebo.py-9]                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
go2_ros2    | 2026-05-18 11:48:53.950 | [robot_controller_gazebo.py-9]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/executors.py", line 877, in wait_for_ready_callbacks
go2_ros2    | 2026-05-18 11:48:53.950 | [robot_controller_gazebo.py-9]     return next(self._cb_iter)
go2_ros2    | 2026-05-18 11:48:53.950 | [robot_controller_gazebo.py-9]            ^^^^^^^^^^^^^^^^^^^
go2_ros2    | 2026-05-18 11:48:53.950 | [robot_controller_gazebo.py-9]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/executors.py", line 781, in _wait_for_ready_callbacks
go2_ros2    | 2026-05-18 11:48:53.956 | [robot_controller_gazebo.py-9]     wait_set.wait(timeout_nsec)
go2_ros2    | 2026-05-18 11:48:53.956 | [robot_controller_gazebo.py-9] KeyboardInterrupt
go2_ros2    | 2026-05-18 11:48:53.958 | [controller_server-23] [INFO] [1779079733.674736503] [controller_server]: Destroying
go2_ros2    | 2026-05-18 11:48:53.959 | [image_bridge-7] [INFO] [1779079733.680574800] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:48:53.962 | [QuadrupedOdometryNode.py-10] Traceback (most recent call last):
go2_ros2    | 2026-05-18 11:48:53.962 | [QuadrupedOdometryNode.py-10]   File "/ros2_ws/install/go2_sim/lib/go2_sim/QuadrupedOdometryNode.py", line 470, in <module>
go2_ros2    | 2026-05-18 11:48:53.963 | [QuadrupedOdometryNode.py-10]     main()
go2_ros2    | 2026-05-18 11:48:53.964 | [QuadrupedOdometryNode.py-10]   File "/ros2_ws/install/go2_sim/lib/go2_sim/QuadrupedOdometryNode.py", line 467, in main
go2_ros2    | 2026-05-18 11:48:53.964 | [QuadrupedOdometryNode.py-10]     rclpy.shutdown()
go2_ros2    | 2026-05-18 11:48:53.965 | [QuadrupedOdometryNode.py-10]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/__init__.py", line 134, in shutdown
go2_ros2    | 2026-05-18 11:48:53.965 | [QuadrupedOdometryNode.py-10]     _shutdown(context=context)
go2_ros2    | 2026-05-18 11:48:53.965 | [QuadrupedOdometryNode.py-10]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/utilities.py", line 82, in shutdown
go2_ros2    | 2026-05-18 11:48:53.965 | [QuadrupedOdometryNode.py-10]     context.shutdown()
go2_ros2    | 2026-05-18 11:48:53.965 | [QuadrupedOdometryNode.py-10]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/context.py", line 129, in shutdown
go2_ros2    | 2026-05-18 11:48:53.966 | [QuadrupedOdometryNode.py-10]     self.__context.shutdown()
go2_ros2    | 2026-05-18 11:48:53.967 | [QuadrupedOdometryNode.py-10] rclpy._rclpy_pybind11.RCLError: failed to shutdown: rcl_shutdown already called on the given context, at ./src/rcl/init.c:333
go2_ros2    | 2026-05-18 11:48:53.974 | [INFO] [robot_state_publisher-3]: process has finished cleanly [pid 73]
go2_ros2    | 2026-05-18 11:48:53.975 | [parameter_bridge-6] [INFO] [1779079733.725768669] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:48:53.975 | [cmd_vel_pub.py-8] Traceback (most recent call last):
go2_ros2    | 2026-05-18 11:48:53.975 | [cmd_vel_pub.py-8]   File "/ros2_ws/install/go2_sim/lib/go2_sim/cmd_vel_pub.py", line 115, in <module>
go2_ros2    | 2026-05-18 11:48:53.976 | [cmd_vel_pub.py-8]     main()
go2_ros2    | 2026-05-18 11:48:53.976 | [cmd_vel_pub.py-8]   File "/ros2_ws/install/go2_sim/lib/go2_sim/cmd_vel_pub.py", line 112, in main
go2_ros2    | 2026-05-18 11:48:53.976 | [cmd_vel_pub.py-8]     rclpy.shutdown()
go2_ros2    | 2026-05-18 11:48:53.976 | [cmd_vel_pub.py-8]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/__init__.py", line 134, in shutdown
go2_ros2    | 2026-05-18 11:48:53.976 | [cmd_vel_pub.py-8]     _shutdown(context=context)
go2_ros2    | 2026-05-18 11:48:53.976 | [cmd_vel_pub.py-8]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/utilities.py", line 82, in shutdown
go2_ros2    | 2026-05-18 11:48:53.976 | [cmd_vel_pub.py-8]     context.shutdown()
go2_ros2    | 2026-05-18 11:48:53.976 | [cmd_vel_pub.py-8]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/context.py", line 129, in shutdown
go2_ros2    | 2026-05-18 11:48:53.976 | [cmd_vel_pub.py-8]     self.__context.shutdown()
go2_ros2    | 2026-05-18 11:48:53.976 | [cmd_vel_pub.py-8] rclpy._rclpy_pybind11.RCLError: failed to shutdown: rcl_shutdown already called on the given context, at ./src/rcl/init.c:333
go2_ros2    | 2026-05-18 11:48:53.977 | [parameter_bridge-5] [INFO] [1779079733.763478269] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:48:53.978 | [ERROR] [robot_controller_gazebo.py-9]: process has died [pid 79, exit code -2, cmd '/ros2_ws/install/go2_sim/lib/go2_sim/robot_controller_gazebo.py --ros-args -r __node:=quadruped_controller -r __ns:=/go2 --params-file /tmp/launch_params__g6a_phe'].
go2_ros2    | 2026-05-18 11:48:53.979 | [robot_state_publisher-3] [INFO] [1779079733.791466072] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:48:53.979 | [robot_state_publisher-2] [INFO] [1779079733.825106913] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:48:54.029 | [INFO] [robot_state_publisher-2]: process has finished cleanly [pid 72]
go2_ros2    | 2026-05-18 11:48:54.054 | [ERROR] [cmd_vel_pub.py-8]: process has died [pid 78, exit code 1, cmd '/ros2_ws/install/go2_sim/lib/go2_sim/cmd_vel_pub.py --ros-args -r __node:=cmd_vel_pub -r __ns:=/go2 --params-file /tmp/launch_params_cn49m0jf -r cmd_vel:=/cmd_vel_out'].
go2_ros2    | 2026-05-18 11:48:54.083 | [ERROR] [QuadrupedOdometryNode.py-10]: process has died [pid 80, exit code 1, cmd '/ros2_ws/install/go2_sim/lib/go2_sim/QuadrupedOdometryNode.py --ros-args -r __node:=quadruped_odom --params-file /tmp/launch_params_iwmkl8r_ -r imu_plugin/out:=/go2/imu_plugin/out -r robot_velocity:=/go2/robot_velocity -r joint_group_controller/commands:=/go2/joint_group_controller/commands -r foot_contact:=/go2/foot_contact'].
go2_ros2    | 2026-05-18 11:48:54.547 | [INFO] [foxglove_bridge-21]: process has finished cleanly [pid 97]
ollama      | 2026-05-18 11:48:56.666 | [GIN] 2026/05/18 - 04:48:56 | 200 |      43.426µs |       127.0.0.1 | HEAD     "/"
ollama      | 2026-05-18 11:48:56.667 | [GIN] 2026/05/18 - 04:48:56 | 200 |     401.209µs |       127.0.0.1 | GET      "/api/tags"
go2_ros2    | 2026-05-18 11:48:57.936 | [ERROR] [lifecycle_manager-33]: process[lifecycle_manager-33] failed to terminate '5' seconds after receiving 'SIGINT', escalating to 'SIGTERM'
go2_ros2    | 2026-05-18 11:48:57.943 | [ERROR] [planner_server-25]: process[planner_server-25] failed to terminate '5' seconds after receiving 'SIGINT', escalating to 'SIGTERM'
go2_ros2    | 2026-05-18 11:48:57.945 | [INFO] [lifecycle_manager-33]: sending signal 'SIGTERM' to process[lifecycle_manager-33]
go2_ros2    | 2026-05-18 11:48:57.950 | [INFO] [planner_server-25]: sending signal 'SIGTERM' to process[planner_server-25]
go2_ros2    | 2026-05-18 11:48:57.954 | [planner_server-25] [INFO] [1779079737.950075985] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:48:59.350 | [planner_server-25] [INFO] [1779079739.350104475] [planner_server]: Destroying plugin GridBased of type SmacPlannerHybrid
go2_ros2    | 2026-05-18 11:48:59.350 | [planner_server-25] [FATAL] [1779079739.350255600] [planner_server]: Failed to create global planner. Exception: could not create publisher: rcl node's context is invalid, at ./src/rcl/node.c:404
go2_ros2    | 2026-05-18 11:48:59.350 | [planner_server-25] [INFO] [1779079739.350261172] [planner_server]: Cleaning up
go2_ros2    | 2026-05-18 11:48:59.350 | [planner_server-25] [ERROR] [1779079739.350277704] [global_costmap.global_costmap]: Unable to start transition 2 from current state cleaningup: Could not publish transition: publisher's context is invalid, at ./src/rcl/publisher.c:423, at ./src/rcl_lifecycle.c:368
go2_ros2    | 2026-05-18 11:48:59.351 | [planner_server-25] [ERROR] [1779079739.350341348] [planner_server]: Failed to finish transition 1. Current state is now: unconfigured (Could not publish transition: publisher's context is invalid, at ./src/rcl/publisher.c:423, at ./src/rcl_lifecycle.c:368)
go2_ros2    | 2026-05-18 11:48:59.354 | [planner_server-25] Warning: class_loader.ClassLoader: SEVERE WARNING!!! Attempting to unload library while objects created by this loader exist in the heap! You should delete your objects before attempting to unload the library or destroying the ClassLoader. The library will NOT be unloaded.
go2_ros2    | 2026-05-18 11:48:59.354 | [planner_server-25]          at line 127 in ./src/class_loader.cpp
go2_ros2    | 2026-05-18 11:48:59.391 | [planner_server-25] [INFO] [1779079739.390586447] [global_costmap.global_costmap]: Destroying
go2_ros2    | 2026-05-18 11:48:59.391 | [planner_server-25] [WARN] [1779079739.390662724] [rcl_lifecycle]: No transition matching 2 found for current state cleaningup
go2_ros2    | 2026-05-18 11:48:59.398 | [planner_server-25] [INFO] [1779079739.397203380] [planner_server]: Destroying
go2_ros2    | 2026-05-18 11:48:59.515 | [INFO] [planner_server-25]: process has finished cleanly [pid 113]
go2_ros2    | 2026-05-18 11:49:01.351 | [lifecycle_manager-33] [ERROR] [1779079741.351146511] [lifecycle_manager_navigation]: Failed to change state for node: planner_server. Exception: planner_server/get_state service client: async_send_request failed.
go2_ros2    | 2026-05-18 11:49:01.351 | [lifecycle_manager-33] [ERROR] [1779079741.351269124] [lifecycle_manager_navigation]: Failed to bring up all requested nodes. Aborting bringup.
go2_ros2    | 2026-05-18 11:49:01.357 | [lifecycle_manager-33] [INFO] [1779079741.357388000] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:49:01.357 | [lifecycle_manager-33] [INFO] [1779079741.357473096] [lifecycle_manager_navigation]: Destroying lifecycle_manager_navigation
go2_ros2    | 2026-05-18 11:49:01.468 | [INFO] [lifecycle_manager-33]: process has finished cleanly [pid 265]
go2_ros2    | 2026-05-18 11:49:04.277 | (EE) 
go2_ros2    | 2026-05-18 11:49:04.277 | Fatal server error:
go2_ros2    | 2026-05-18 11:49:04.277 | (EE) Server is already active for display 1
go2_ros2    | 2026-05-18 11:49:04.277 | 	If this server is no longer running, remove /tmp/.X1-lock
go2_ros2    | 2026-05-18 11:49:04.277 | 	and start again.
go2_ros2    | 2026-05-18 11:49:04.277 | (EE) 
go2_ros2    | 2026-05-18 11:49:05.274 | VNC server started — connect to localhost:5901 with password 'ros2vnc'
go2_ros2    | 2026-05-18 11:49:05.274 | Mode: SIMULATION (USE_SIM=true)
go2_ros2    | 2026-05-18 11:49:05.275 | /usr/bin/startxfce4: X server already running on display :1
go2_ros2    | 2026-05-18 11:49:05.280 | xrdb: Connection refused
go2_ros2    | 2026-05-18 11:49:05.280 | xrdb: Can't open display ':1'
go2_ros2    | 2026-05-18 11:49:05.282 | 
go2_ros2    | 2026-05-18 11:49:05.282 | 18/05/2026 04:49:05 ***************************************
go2_ros2    | 2026-05-18 11:49:05.282 | 18/05/2026 04:49:05 *** XOpenDisplay failed (:1)
go2_ros2    | 2026-05-18 11:49:05.282 | 
go2_ros2    | 2026-05-18 11:49:05.282 | *** x11vnc was unable to open the X DISPLAY: ":1", it cannot continue.
go2_ros2    | 2026-05-18 11:49:05.282 | *** There may be "Xlib:" error messages above with details about the failure.
go2_ros2    | 2026-05-18 11:49:05.282 | 
go2_ros2    | 2026-05-18 11:49:05.282 | Some tips and guidelines:
go2_ros2    | 2026-05-18 11:49:05.282 | 
go2_ros2    | 2026-05-18 11:49:05.282 | ** An X server (the one you wish to view) must be running before x11vnc is
go2_ros2    | 2026-05-18 11:49:05.282 |    started: x11vnc does not start the X server.  (however, see the -create
go2_ros2    | 2026-05-18 11:49:05.282 |    option if that is what you really want).
go2_ros2    | 2026-05-18 11:49:05.282 | 
go2_ros2    | 2026-05-18 11:49:05.282 | ** You must use -display <disp>, -OR- set and export your $DISPLAY
go2_ros2    | 2026-05-18 11:49:05.282 |    environment variable to refer to the display of the desired X server.
go2_ros2    | 2026-05-18 11:49:05.282 |  - Usually the display is simply ":0" (in fact x11vnc uses this if you forget
go2_ros2    | 2026-05-18 11:49:05.282 |    to specify it), but in some multi-user situations it could be ":1", ":2",
go2_ros2    | 2026-05-18 11:49:05.282 |    or even ":137".  Ask your administrator or a guru if you are having
go2_ros2    | 2026-05-18 11:49:05.282 |    difficulty determining what your X DISPLAY is.
go2_ros2    | 2026-05-18 11:49:05.282 | 
go2_ros2    | 2026-05-18 11:49:05.282 | ** Next, you need to have sufficient permissions (Xauthority) 
go2_ros2    | 2026-05-18 11:49:05.282 |    to connect to the X DISPLAY.   Here are some Tips:
go2_ros2    | 2026-05-18 11:49:05.282 | 
go2_ros2    | 2026-05-18 11:49:05.282 |  - Often, you just need to run x11vnc as the user logged into the X session.
go2_ros2    | 2026-05-18 11:49:05.282 |    So make sure to be that user when you type x11vnc.
go2_ros2    | 2026-05-18 11:49:05.282 |  - Being root is usually not enough because the incorrect MIT-MAGIC-COOKIE
go2_ros2    | 2026-05-18 11:49:05.282 |    file may be accessed.  The cookie file contains the secret key that
go2_ros2    | 2026-05-18 11:49:05.282 |    allows x11vnc to connect to the desired X DISPLAY.
go2_ros2    | 2026-05-18 11:49:05.282 |  - You can explicitly indicate which MIT-MAGIC-COOKIE file should be used
go2_ros2    | 2026-05-18 11:49:05.282 |    by the -auth option, e.g.:
go2_ros2    | 2026-05-18 11:49:05.282 |        x11vnc -auth /home/someuser/.Xauthority -display :0
go2_ros2    | 2026-05-18 11:49:05.282 |        x11vnc -auth /tmp/.gdmzndVlR -display :0
go2_ros2    | 2026-05-18 11:49:05.282 |    you must have read permission for the auth file.
go2_ros2    | 2026-05-18 11:49:05.282 |    See also '-auth guess' and '-findauth' discussed below.
go2_ros2    | 2026-05-18 11:49:05.282 | 
go2_ros2    | 2026-05-18 11:49:05.282 | ** If NO ONE is logged into an X session yet, but there is a greeter login
go2_ros2    | 2026-05-18 11:49:05.282 |    program like "gdm", "kdm", "xdm", or "dtlogin" running, you will need
go2_ros2    | 2026-05-18 11:49:05.282 |    to find and use the raw display manager MIT-MAGIC-COOKIE file.
go2_ros2    | 2026-05-18 11:49:05.282 |    Some examples for various display managers:
go2_ros2    | 2026-05-18 11:49:05.282 | 
go2_ros2    | 2026-05-18 11:49:05.282 |      gdm:     -auth /var/gdm/:0.Xauth
go2_ros2    | 2026-05-18 11:49:05.282 |               -auth /var/lib/gdm/:0.Xauth
go2_ros2    | 2026-05-18 11:49:05.282 |      kdm:     -auth /var/lib/kdm/A:0-crWk72
go2_ros2    | 2026-05-18 11:49:05.282 |               -auth /var/run/xauth/A:0-crWk72
go2_ros2    | 2026-05-18 11:49:05.282 |      xdm:     -auth /var/lib/xdm/authdir/authfiles/A:0-XQvaJk
go2_ros2    | 2026-05-18 11:49:05.282 |      dtlogin: -auth /var/dt/A:0-UgaaXa
go2_ros2    | 2026-05-18 11:49:05.282 | 
go2_ros2    | 2026-05-18 11:49:05.282 |    Sometimes the command "ps wwwwaux | grep auth" can reveal the file location.
go2_ros2    | 2026-05-18 11:49:05.282 | 
go2_ros2    | 2026-05-18 11:49:05.282 |    Starting with x11vnc 0.9.9 you can have it try to guess by using:
go2_ros2    | 2026-05-18 11:49:05.282 | 
go2_ros2    | 2026-05-18 11:49:05.282 |               -auth guess
go2_ros2    | 2026-05-18 11:49:05.282 | 
go2_ros2    | 2026-05-18 11:49:05.282 |    (see also the x11vnc -findauth option.)
go2_ros2    | 2026-05-18 11:49:05.282 | 
go2_ros2    | 2026-05-18 11:49:05.282 |    Only root will have read permission for the file, and so x11vnc must be run
go2_ros2    | 2026-05-18 11:49:05.282 |    as root (or copy it).  The random characters in the filenames will of course
go2_ros2    | 2026-05-18 11:49:05.282 |    change and the directory the cookie file resides in is system dependent.
go2_ros2    | 2026-05-18 11:49:05.282 | 
go2_ros2    | 2026-05-18 11:49:05.282 | See also: http://www.karlrunge.com/x11vnc/faq.html
go2_ros2    | 2026-05-18 11:49:05.322 | xfce4-session: Cannot open display: .
go2_ros2    | 2026-05-18 11:49:05.322 | Type 'xfce4-session --help' for usage.
go2_ros2    | 2026-05-18 11:49:05.536 | [INFO] [launch]: All log files can be found below /root/.ros/log/2026-05-18-04-49-05-535099-58bd4d7bd85c-1
go2_ros2    | 2026-05-18 11:49:05.536 | [INFO] [launch]: Default logging verbosity is set to INFO
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [gazebo-1]: process started with pid [70]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [robot_state_publisher-2]: process started with pid [71]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [robot_state_publisher-3]: process started with pid [73]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [create-4]: process started with pid [74]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [parameter_bridge-5]: process started with pid [75]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [parameter_bridge-6]: process started with pid [76]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [image_bridge-7]: process started with pid [77]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [cmd_vel_pub.py-8]: process started with pid [78]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [robot_controller_gazebo.py-9]: process started with pid [79]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [QuadrupedOdometryNode.py-10]: process started with pid [80]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [relay-11]: process started with pid [81]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [relay-12]: process started with pid [82]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [relay-13]: process started with pid [83]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [relay-14]: process started with pid [84]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [relay-15]: process started with pid [85]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [sim_cmd_node.py-16]: process started with pid [86]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [joy_node-17]: process started with pid [87]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [teleop_node-18]: process started with pid [90]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [twist_mux-19]: process started with pid [91]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [rviz2-20]: process started with pid [98]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [foxglove_bridge-21]: process started with pid [101]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [async_slam_toolbox_node-22]: process started with pid [120]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [controller_server-23]: process started with pid [128]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [smoother_server-24]: process started with pid [132]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [planner_server-25]: process started with pid [140]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [route_server-26]: process started with pid [147]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [behavior_server-27]: process started with pid [161]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [bt_navigator-28]: process started with pid [202]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [waypoint_follower-29]: process started with pid [206]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [velocity_smoother-30]: process started with pid [214]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [collision_monitor-31]: process started with pid [226]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [opennav_docking-32]: process started with pid [236]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [lifecycle_manager-33]: process started with pid [238]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [mic_bridge_node-34]: process started with pid [241]
go2_ros2    | 2026-05-18 11:49:06.506 | [INFO] [voice_cmd_node-35]: process started with pid [243]
go2_ros2    | 2026-05-18 11:49:06.512 | [create-4] [INFO] [1779079746.473158441] [spawn_go2]: Requesting list of world names.
go2_ros2    | 2026-05-18 11:49:06.512 | [rviz2-20] qt.qpa.xcb: could not connect to display :1
go2_ros2    | 2026-05-18 11:49:06.513 | [rviz2-20] qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.
go2_ros2    | 2026-05-18 11:49:06.513 | [rviz2-20] This application failed to start because no Qt platform plugin could be initialized. Reinstalling the application may fix this problem.
go2_ros2    | 2026-05-18 11:49:06.513 | [rviz2-20] 
go2_ros2    | 2026-05-18 11:49:06.513 | [rviz2-20] Available platform plugins are: eglfs, linuxfb, minimal, minimalegl, offscreen, vnc, xcb.
go2_ros2    | 2026-05-18 11:49:06.513 | [rviz2-20] 
go2_ros2    | 2026-05-18 11:49:06.923 | [ERROR] [rviz2-20]: process has died [pid 98, exit code -6, cmd '/opt/ros/jazzy/lib/rviz2/rviz2 -d /ros2_ws/install/go2_robot_sdk/share/go2_robot_sdk/config/single_robot_conf_sim.rviz --ros-args -r __node:=go2_rviz2 --params-file /tmp/launch_params_iehbb3yb'].
go2_ros2    | 2026-05-18 11:49:07.007 | [gazebo-1] qt.qpa.xcb: could not connect to display :1
go2_ros2    | 2026-05-18 11:49:07.008 | [gazebo-1] qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.
go2_ros2    | 2026-05-18 11:49:07.008 | [gazebo-1] This application failed to start because no Qt platform plugin could be initialized. Reinstalling the application may fix this problem.
go2_ros2    | 2026-05-18 11:49:07.008 | [gazebo-1] 
go2_ros2    | 2026-05-18 11:49:07.008 | [gazebo-1] Available platform plugins are: eglfs, linuxfb, minimal, minimalegl, offscreen, vnc, xcb.
go2_ros2    | 2026-05-18 11:49:07.009 | [gazebo-1] 
go2_ros2    | 2026-05-18 11:49:07.009 | [gazebo-1] Stack trace (most recent call last):
go2_ros2    | 2026-05-18 11:49:07.010 | [gazebo-1] #31   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x735ac9750152, in ruby_run_node
go2_ros2    | 2026-05-18 11:49:07.010 | [gazebo-1] #30   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x735ac974be2b, in 
go2_ros2    | 2026-05-18 11:49:07.010 | [gazebo-1] #29   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x735ac98eeb49, in rb_vm_exec
go2_ros2    | 2026-05-18 11:49:07.010 | [gazebo-1] #28   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x735ac98eb62b, in 
go2_ros2    | 2026-05-18 11:49:07.010 | [gazebo-1] #27   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x735ac98e713e, in 
go2_ros2    | 2026-05-18 11:49:07.010 | [gazebo-1] #26   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x735ac98e492f, in 
go2_ros2    | 2026-05-18 11:49:07.010 | [gazebo-1] #25   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x735ac9825049, in 
go2_ros2    | 2026-05-18 11:49:07.010 | [gazebo-1] #24   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x735ac974e1d6, in rb_protect
go2_ros2    | 2026-05-18 11:49:07.010 | [gazebo-1] #23   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x735ac98f32d9, in rb_yield
go2_ros2    | 2026-05-18 11:49:07.010 | [gazebo-1] #22   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x735ac98eeb49, in rb_vm_exec
go2_ros2    | 2026-05-18 11:49:07.010 | [gazebo-1] #21   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x735ac98eb62b, in 
go2_ros2    | 2026-05-18 11:49:07.011 | [gazebo-1] #20   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x735ac98e713e, in 
go2_ros2    | 2026-05-18 11:49:07.012 | [gazebo-1] #19   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x735ac98e492f, in 
go2_ros2    | 2026-05-18 11:49:07.013 | [gazebo-1] #18   Object "/usr/lib/x86_64-linux-gnu/ruby/3.2.0/fiddle.so", at 0x735ac4a7cb13, in 
go2_ros2    | 2026-05-18 11:49:07.013 | [gazebo-1] #17   Object "/usr/lib/x86_64-linux-gnu/libruby-3.2.so.3.2", at 0x735ac98ad37b, in rb_nogvl
go2_ros2    | 2026-05-18 11:49:07.013 | [gazebo-1] #16   Object "/usr/lib/x86_64-linux-gnu/ruby/3.2.0/fiddle.so", at 0x735ac4a7c43b, in 
go2_ros2    | 2026-05-18 11:49:07.014 | [gazebo-1] #15   Object "/usr/lib/x86_64-linux-gnu/libffi.so.8", at 0x735ac4a1c0bd, in ffi_call
go2_ros2    | 2026-05-18 11:49:07.014 | [gazebo-1] #14   Object "/usr/lib/x86_64-linux-gnu/libffi.so.8", at 0x735ac4a193ee, in 
go2_ros2    | 2026-05-18 11:49:07.014 | [gazebo-1] #13   Object "/usr/lib/x86_64-linux-gnu/libffi.so.8", at 0x735ac4a1cb15, in 
go2_ros2    | 2026-05-18 11:49:07.014 | [gazebo-1] #12   Object "/opt/ros/jazzy/opt/gz_sim_vendor/lib/libgz-sim8-gz.so.8.11.0", at 0x735ac3eefdb2, in runGui
go2_ros2    | 2026-05-18 11:49:07.014 | [gazebo-1] #11   Object "/opt/ros/jazzy/opt/gz_sim_vendor/lib/libgz-sim8-gui.so.8", at 0x735ac3d3c33c, in gz::sim::v8::gui::runGui(int&, char**, char const*, char const*, int, char const*, char const*)
go2_ros2    | 2026-05-18 11:49:07.014 | [gazebo-1] #10   Object "/opt/ros/jazzy/opt/gz_sim_vendor/lib/libgz-sim8-gui.so.8", at 0x735ac3d396d9, in gz::sim::v8::gui::createGui(int&, char**, char const*, char const*, bool, char const*, int, char const*, char const*)
go2_ros2    | 2026-05-18 11:49:07.014 | [gazebo-1] #9    Object "/opt/ros/jazzy/opt/gz_gui_vendor/lib/libgz-gui8.so.8", at 0x735ac2a9efdc, in gz::gui::Application::Application(int&, char**, gz::gui::WindowType, char const*)
go2_ros2    | 2026-05-18 11:49:07.014 | [gazebo-1] #8    Object "/usr/lib/x86_64-linux-gnu/libQt5Widgets.so.5", at 0x735ac251f5b4, in QApplicationPrivate::init()
ollama      | 2026-05-18 11:49:07.014 | [GIN] 2026/05/18 - 04:49:07 | 200 |      34.884µs |       127.0.0.1 | HEAD     "/"
go2_ros2    | 2026-05-18 11:49:07.015 | [gazebo-1] #7    Object "/usr/lib/x86_64-linux-gnu/libQt5Gui.so.5", at 0x735ac13f6b9e, in QGuiApplicationPrivate::init()
go2_ros2    | 2026-05-18 11:49:07.015 | [gazebo-1] #6    Object "/usr/lib/x86_64-linux-gnu/libQt5Core.so.5", at 0x735ac2de4ff4, in QCoreApplicationPrivate::init()
go2_ros2    | 2026-05-18 11:49:07.015 | [gazebo-1] #5    Object "/usr/lib/x86_64-linux-gnu/libQt5Gui.so.5", at 0x735ac13f3c1f, in QGuiApplicationPrivate::createEventDispatcher()
go2_ros2    | 2026-05-18 11:49:07.015 | [gazebo-1] #4    Object "/usr/lib/x86_64-linux-gnu/libQt5Gui.so.5", at 0x735ac13f36dc, in QGuiApplicationPrivate::createPlatformIntegration()
go2_ros2    | 2026-05-18 11:49:07.015 | [gazebo-1] #3    Object "/usr/lib/x86_64-linux-gnu/libQt5Core.so.5", at 0x735ac2b97103, in QMessageLogger::fatal(char const*, ...) const
ollama      | 2026-05-18 11:49:07.015 | [GIN] 2026/05/18 - 04:49:07 | 200 |     425.075µs |       127.0.0.1 | GET      "/api/tags"
go2_ros2    | 2026-05-18 11:49:07.015 | [gazebo-1] #2    Object "/usr/lib/x86_64-linux-gnu/libc.so.6", at 0x735ac92e88fe, in abort
go2_ros2    | 2026-05-18 11:49:07.015 | [gazebo-1] #1    Object "/usr/lib/x86_64-linux-gnu/libc.so.6", at 0x735ac930527d, in gsignal
go2_ros2    | 2026-05-18 11:49:07.018 | [gazebo-1] #0    Object "/usr/lib/x86_64-linux-gnu/libc.so.6", at 0x735ac935eb2c, in pthread_kill
go2_ros2    | 2026-05-18 11:49:07.018 | [gazebo-1] Aborted (Signal sent by tkill() 558 0)
go2_ros2    | 2026-05-18 11:49:07.174 | [parameter_bridge-6] [INFO] [1779079747.170249609] [go2_gz_bridge_sensors]: Creating GZ->ROS Bridge: [/go2/imu_plugin/out (gz.msgs.IMU) -> /go2/imu_plugin/out (sensor_msgs/msg/Imu)] (Lazy 0)
go2_ros2    | 2026-05-18 11:49:07.179 | [parameter_bridge-6] [INFO] [1779079747.179043048] [go2_gz_bridge_sensors]: Creating ROS->GZ Bridge: [/go2/imu_plugin/out (sensor_msgs/msg/Imu) -> /go2/imu_plugin/out (gz.msgs.IMU)] (Lazy 0)
go2_ros2    | 2026-05-18 11:49:07.204 | [parameter_bridge-6] [INFO] [1779079747.203568638] [go2_gz_bridge_sensors]: Creating GZ->ROS Bridge: [/go2/scan (gz.msgs.LaserScan) -> /go2/scan (sensor_msgs/msg/LaserScan)] (Lazy 0)
go2_ros2    | 2026-05-18 11:49:07.287 | [parameter_bridge-6] [INFO] [1779079747.286469319] [go2_gz_bridge_sensors]: Creating ROS->GZ Bridge: [/go2/scan (sensor_msgs/msg/LaserScan) -> /go2/scan (gz.msgs.LaserScan)] (Lazy 0)
go2_ros2    | 2026-05-18 11:49:07.302 | [lifecycle_manager-33] [INFO] [1779079747.301183604] [lifecycle_manager_navigation]: Creating
go2_ros2    | 2026-05-18 11:49:07.306 | [robot_state_publisher-3] [INFO] [1779079747.305428038] [go2.go2_robot_state_publisher_ns]: Robot initialized
go2_ros2    | 2026-05-18 11:49:07.333 | [parameter_bridge-6] [INFO] [1779079747.332296813] [go2_gz_bridge_sensors]: Creating GZ->ROS Bridge: [/go2/color/image_raw (gz.msgs.Image) -> /go2/color/image_raw (sensor_msgs/msg/Image)] (Lazy 0)
go2_ros2    | 2026-05-18 11:49:07.369 | [route_server-26] [INFO] [1779079747.368977671] [route_server]: 
go2_ros2    | 2026-05-18 11:49:07.369 | [route_server-26] 	route_server lifecycle node launched. 
go2_ros2    | 2026-05-18 11:49:07.369 | [route_server-26] 	Waiting on external lifecycle transitions to activate
go2_ros2    | 2026-05-18 11:49:07.369 | [route_server-26] 	See https://design.ros2.org/articles/node_lifecycle.html for more information.
go2_ros2    | 2026-05-18 11:49:07.401 | [controller_server-23] [INFO] [1779079747.400540273] [controller_server]: 
go2_ros2    | 2026-05-18 11:49:07.401 | [controller_server-23] 	controller_server lifecycle node launched. 
go2_ros2    | 2026-05-18 11:49:07.402 | [controller_server-23] 	Waiting on external lifecycle transitions to activate
go2_ros2    | 2026-05-18 11:49:07.402 | [controller_server-23] 	See https://design.ros2.org/articles/node_lifecycle.html for more information.
go2_ros2    | 2026-05-18 11:49:07.406 | [parameter_bridge-6] [INFO] [1779079747.404056473] [go2_gz_bridge_sensors]: Creating ROS->GZ Bridge: [/go2/color/image_raw (sensor_msgs/msg/Image) -> /go2/color/image_raw (gz.msgs.Image)] (Lazy 0)
go2_ros2    | 2026-05-18 11:49:07.410 | [controller_server-23] [INFO] [1779079747.408852660] [controller_server]: Creating controller server
go2_ros2    | 2026-05-18 11:49:07.411 | [parameter_bridge-6] [INFO] [1779079747.409655749] [go2_gz_bridge_sensors]: Creating GZ->ROS Bridge: [/go2/color/camera_info (gz.msgs.CameraInfo) -> /go2/color/camera_info (sensor_msgs/msg/CameraInfo)] (Lazy 0)
go2_ros2    | 2026-05-18 11:49:07.420 | [parameter_bridge-6] [INFO] [1779079747.418519728] [go2_gz_bridge_sensors]: Creating ROS->GZ Bridge: [/go2/color/camera_info (sensor_msgs/msg/CameraInfo) -> /go2/color/camera_info (gz.msgs.CameraInfo)] (Lazy 0)
go2_ros2    | 2026-05-18 11:49:07.420 | [lifecycle_manager-33] [INFO] [1779079747.419018791] [lifecycle_manager_navigation]: Creating and initializing lifecycle service clients
go2_ros2    | 2026-05-18 11:49:07.426 | [waypoint_follower-29] [INFO] [1779079747.425716590] [waypoint_follower]: 
go2_ros2    | 2026-05-18 11:49:07.426 | [waypoint_follower-29] 	waypoint_follower lifecycle node launched. 
go2_ros2    | 2026-05-18 11:49:07.426 | [waypoint_follower-29] 	Waiting on external lifecycle transitions to activate
go2_ros2    | 2026-05-18 11:49:07.426 | [waypoint_follower-29] 	See https://design.ros2.org/articles/node_lifecycle.html for more information.
go2_ros2    | 2026-05-18 11:49:07.427 | [waypoint_follower-29] [INFO] [1779079747.427016070] [waypoint_follower]: Creating
go2_ros2    | 2026-05-18 11:49:07.435 | [opennav_docking-32] [INFO] [1779079747.431634613] [docking_server]: 
go2_ros2    | 2026-05-18 11:49:07.435 | [opennav_docking-32] 	docking_server lifecycle node launched. 
go2_ros2    | 2026-05-18 11:49:07.435 | [opennav_docking-32] 	Waiting on external lifecycle transitions to activate
go2_ros2    | 2026-05-18 11:49:07.435 | [opennav_docking-32] 	See https://design.ros2.org/articles/node_lifecycle.html for more information.
go2_ros2    | 2026-05-18 11:49:07.435 | [opennav_docking-32] [INFO] [1779079747.431796112] [docking_server]: Creating docking_server
go2_ros2    | 2026-05-18 11:49:07.442 | [twist_mux-19] [INFO] [1779079747.439635270] [twist_mux]: Topic handler 'topics.foxglove' subscribed to topic 'cmd_vel_foxglove': timeout = 0.500000s , priority = 8.
go2_ros2    | 2026-05-18 11:49:07.447 | [collision_monitor-31] [INFO] [1779079747.445603703] [collision_monitor]: 
go2_ros2    | 2026-05-18 11:49:07.447 | [collision_monitor-31] 	collision_monitor lifecycle node launched. 
go2_ros2    | 2026-05-18 11:49:07.447 | [collision_monitor-31] 	Waiting on external lifecycle transitions to activate
go2_ros2    | 2026-05-18 11:49:07.447 | [collision_monitor-31] 	See https://design.ros2.org/articles/node_lifecycle.html for more information.
go2_ros2    | 2026-05-18 11:49:07.467 | [async_slam_toolbox_node-22] [INFO] [1779079747.466360380] [slam_toolbox]: Node using stack size 40000000
go2_ros2    | 2026-05-18 11:49:07.467 | [teleop_node-18] [INFO] [1779079747.466976213] [TeleopTwistJoy]: Linear axis x on 1 at scale 0.500000.
go2_ros2    | 2026-05-18 11:49:07.468 | [teleop_node-18] [INFO] [1779079747.467024907] [TeleopTwistJoy]: Linear axis y on 3 at scale 0.500000.
go2_ros2    | 2026-05-18 11:49:07.468 | [teleop_node-18] [INFO] [1779079747.467030553] [TeleopTwistJoy]: Angular axis yaw on 6 at scale 1.000000.
go2_ros2    | 2026-05-18 11:49:07.476 | [controller_server-23] [INFO] [1779079747.475162152] [local_costmap.local_costmap]: 
go2_ros2    | 2026-05-18 11:49:07.476 | [controller_server-23] 	local_costmap lifecycle node launched. 
go2_ros2    | 2026-05-18 11:49:07.477 | [controller_server-23] 	Waiting on external lifecycle transitions to activate
go2_ros2    | 2026-05-18 11:49:07.477 | [controller_server-23] 	See https://design.ros2.org/articles/node_lifecycle.html for more information.
go2_ros2    | 2026-05-18 11:49:07.477 | [controller_server-23] [INFO] [1779079747.475994347] [local_costmap.local_costmap]: Creating Costmap
go2_ros2    | 2026-05-18 11:49:07.479 | [twist_mux-19] [INFO] [1779079747.478495539] [twist_mux]: Topic handler 'topics.joy' subscribed to topic 'cmd_vel_joy': timeout = 0.500000s , priority = 10.
go2_ros2    | 2026-05-18 11:49:07.497 | [sim_cmd_node.py-16] [INFO] [1779079747.493590995] [sim_cmd_node]: sim_cmd_node ready — publish go2_interfaces/msg/WebRtcReq to /sim_cmd
go2_ros2    | 2026-05-18 11:49:07.506 | [velocity_smoother-30] [INFO] [1779079747.505467277] [velocity_smoother]: 
go2_ros2    | 2026-05-18 11:49:07.507 | [velocity_smoother-30] 	velocity_smoother lifecycle node launched. 
go2_ros2    | 2026-05-18 11:49:07.507 | [velocity_smoother-30] 	Waiting on external lifecycle transitions to activate
go2_ros2    | 2026-05-18 11:49:07.507 | [velocity_smoother-30] 	See https://design.ros2.org/articles/node_lifecycle.html for more information.
go2_ros2    | 2026-05-18 11:49:07.514 | [robot_state_publisher-2] [INFO] [1779079747.512956767] [go2_robot_state_publisher]: Robot initialized
go2_ros2    | 2026-05-18 11:49:07.516 | [twist_mux-19] [INFO] [1779079747.515374377] [twist_mux]: Topic handler 'topics.navigation' subscribed to topic 'cmd_vel': timeout = 0.500000s , priority = 5.
go2_ros2    | 2026-05-18 11:49:07.525 | [twist_mux-19] [INFO] [1779079747.520903137] [twist_mux]: Topic handler 'topics.voice' subscribed to topic 'cmd_vel_voice': timeout = 0.500000s , priority = 7.
go2_ros2    | 2026-05-18 11:49:07.532 | [smoother_server-24] [INFO] [1779079747.530537747] [smoother_server]: 
go2_ros2    | 2026-05-18 11:49:07.532 | [smoother_server-24] 	smoother_server lifecycle node launched. 
go2_ros2    | 2026-05-18 11:49:07.532 | [smoother_server-24] 	Waiting on external lifecycle transitions to activate
go2_ros2    | 2026-05-18 11:49:07.532 | [smoother_server-24] 	See https://design.ros2.org/articles/node_lifecycle.html for more information.
go2_ros2    | 2026-05-18 11:49:07.536 | [smoother_server-24] [INFO] [1779079747.534871195] [smoother_server]: Creating smoother server
go2_ros2    | 2026-05-18 11:49:07.559 | [behavior_server-27] [INFO] [1779079747.558275671] [behavior_server]: 
go2_ros2    | 2026-05-18 11:49:07.559 | [behavior_server-27] 	behavior_server lifecycle node launched. 
go2_ros2    | 2026-05-18 11:49:07.559 | [behavior_server-27] 	Waiting on external lifecycle transitions to activate
go2_ros2    | 2026-05-18 11:49:07.559 | [behavior_server-27] 	See https://design.ros2.org/articles/node_lifecycle.html for more information.
go2_ros2    | 2026-05-18 11:49:07.590 | [planner_server-25] [INFO] [1779079747.589394900] [planner_server]: 
go2_ros2    | 2026-05-18 11:49:07.590 | [planner_server-25] 	planner_server lifecycle node launched. 
go2_ros2    | 2026-05-18 11:49:07.590 | [planner_server-25] 	Waiting on external lifecycle transitions to activate
go2_ros2    | 2026-05-18 11:49:07.590 | [planner_server-25] 	See https://design.ros2.org/articles/node_lifecycle.html for more information.
go2_ros2    | 2026-05-18 11:49:07.595 | [planner_server-25] [INFO] [1779079747.594391632] [planner_server]: Creating
go2_ros2    | 2026-05-18 11:49:07.632 | [foxglove_bridge-21] [INFO] [1779079747.630848907] [foxglove_bridge]: Starting foxglove_bridge (jazzy, 3.2.6@)
go2_ros2    | 2026-05-18 11:49:07.641 | [foxglove_bridge-21] [INFO] [1779079747.639855200] [foxglove_bridge]: Server listening on port 8765
go2_ros2    | 2026-05-18 11:49:07.648 | [foxglove_bridge-21] [INFO] [1779079747.643234235] [foxglove_bridge]: Advertising new channel 1 for topic "/rosout"
go2_ros2    | 2026-05-18 11:49:07.648 | [foxglove_bridge-21] [INFO] [1779079747.644160044] [foxglove_bridge]: Advertising new channel 2 for topic "/parameter_events"
go2_ros2    | 2026-05-18 11:49:07.648 | [foxglove_bridge-21] [INFO] [1779079747.645818068] [foxglove_bridge]: Advertising new channel 3 for topic "/diagnostics"
go2_ros2    | 2026-05-18 11:49:07.649 | [robot_controller_gazebo.py-9] [INFO] [1779079747.644851446] [go2.quadruped_controller]: Переключено на TROT контроллер
go2_ros2    | 2026-05-18 11:49:07.659 | [mic_bridge_node-34] [INFO] [1779079747.646593645] [mic_bridge_node]: MicBridge STT: Gemma local (gemma4:e4b via http://ollama:11434)
go2_ros2    | 2026-05-18 11:49:07.664 | [bt_navigator-28] [INFO] [1779079747.647077937] [bt_navigator]: 
go2_ros2    | 2026-05-18 11:49:07.664 | [bt_navigator-28] 	bt_navigator lifecycle node launched. 
go2_ros2    | 2026-05-18 11:49:07.664 | [bt_navigator-28] 	Waiting on external lifecycle transitions to activate
go2_ros2    | 2026-05-18 11:49:07.664 | [bt_navigator-28] 	See https://design.ros2.org/articles/node_lifecycle.html for more information.
go2_ros2    | 2026-05-18 11:49:07.664 | [bt_navigator-28] [INFO] [1779079747.649469384] [bt_navigator]: Creating
go2_ros2    | 2026-05-18 11:49:07.664 | [mic_bridge_node-34] [INFO] [1779079747.651534946] [mic_bridge_node]: mic_bridge_node ready — open http://localhost:8888 in your host browser
go2_ros2    | 2026-05-18 11:49:07.664 | [mic_bridge_node-34] [INFO] [1779079747.660245503] [mic_bridge_node]: MicBridge HTTP on port 8888
go2_ros2    | 2026-05-18 11:49:07.671 | [foxglove_bridge-21] [INFO] [1779079747.668078348] [foxglove_bridge]: Advertising new channel 4 for topic "/slam_toolbox/transition_event"
go2_ros2    | 2026-05-18 11:49:07.672 | [foxglove_bridge-21] [INFO] [1779079747.668142516] [foxglove_bridge]: Advertising new channel 5 for topic "/collision_monitor/transition_event"
go2_ros2    | 2026-05-18 11:49:07.673 | [foxglove_bridge-21] [INFO] [1779079747.668437888] [foxglove_bridge]: Advertising new channel 6 for topic "/go2/joint_states"
go2_ros2    | 2026-05-18 11:49:07.673 | [foxglove_bridge-21] [INFO] [1779079747.668726197] [foxglove_bridge]: Advertising new channel 7 for topic "/clock"
go2_ros2    | 2026-05-18 11:49:07.680 | [mic_bridge_node-34] [INFO] [1779079747.680034856] [mic_bridge_node]: MicBridge WebSocket on port 8889
go2_ros2    | 2026-05-18 11:49:07.725 | [voice_cmd_node-35] [INFO] [1779079747.722539853] [voice_cmd_node]: NLU: Gemma local (gemma4:e4b via http://ollama:11434)
go2_ros2    | 2026-05-18 11:49:07.725 | [voice_cmd_node-35] [INFO] [1779079747.723480567] [voice_cmd_node]: voice_cmd_node ready — mode=simulation, cmd_topic=/sim_cmd, nlu=gemma_local
go2_ros2    | 2026-05-18 11:49:07.741 | [planner_server-25] [INFO] [1779079747.738776500] [global_costmap.global_costmap]: 
go2_ros2    | 2026-05-18 11:49:07.742 | [planner_server-25] 	global_costmap lifecycle node launched. 
go2_ros2    | 2026-05-18 11:49:07.742 | [planner_server-25] 	Waiting on external lifecycle transitions to activate
go2_ros2    | 2026-05-18 11:49:07.742 | [planner_server-25] 	See https://design.ros2.org/articles/node_lifecycle.html for more information.
go2_ros2    | 2026-05-18 11:49:07.742 | [planner_server-25] [INFO] [1779079747.740078904] [global_costmap.global_costmap]: Creating Costmap
go2_ros2    | 2026-05-18 11:49:07.769 | [QuadrupedOdometryNode.py-10] [INFO] [1779079747.766612184] [quadruped_odom]: Dog Odometry Node has been started.
go2_ros2    | 2026-05-18 11:49:07.826 | [gazebo-1] [Msg] Received world [/ros2_ws/install/go2_sim/share/go2_sim/worlds/cafe.world] from the GUI.
go2_ros2    | 2026-05-18 11:49:07.827 | [gazebo-1] [Msg] Gazebo Sim Server v8.11.0
go2_ros2    | 2026-05-18 11:49:07.827 | [gazebo-1] [Msg] Loading SDF world file[/ros2_ws/install/go2_sim/share/go2_sim/worlds/cafe.world].
go2_ros2    | 2026-05-18 11:49:07.827 | [gazebo-1] [Msg] Serving entity system service on [/entity/system/add]
go2_ros2    | 2026-05-18 11:49:07.827 | [gazebo-1] [Msg] Create service on [/world/default/create_multiple] (async)
go2_ros2    | 2026-05-18 11:49:07.827 | [gazebo-1] [Msg] Create service on [/world/default/create_multiple/blocking] (blocking)
go2_ros2    | 2026-05-18 11:49:07.827 | [gazebo-1] [Msg] Remove service on [/world/default/remove] (async)
go2_ros2    | 2026-05-18 11:49:07.827 | [gazebo-1] [Msg] Remove service on [/world/default/remove/blocking] (blocking)
go2_ros2    | 2026-05-18 11:49:07.827 | [gazebo-1] [Msg] Pose service on [/world/default/set_pose] (async)
go2_ros2    | 2026-05-18 11:49:07.827 | [gazebo-1] [Msg] Pose service on [/world/default/set_pose/blocking] (blocking)
go2_ros2    | 2026-05-18 11:49:07.827 | [gazebo-1] [Msg] Pose service on [/world/default/set_pose_vector] (async)
go2_ros2    | 2026-05-18 11:49:07.827 | [gazebo-1] [Msg] Pose service on [/world/default/set_pose_vector/blocking] (blocking)
go2_ros2    | 2026-05-18 11:49:07.827 | [gazebo-1] [Msg] Light configuration service on [/world/default/light_config] (async)
go2_ros2    | 2026-05-18 11:49:07.827 | [gazebo-1] [Msg] Light configuration service on [/world/default/light_config/blocking] (blocking)
go2_ros2    | 2026-05-18 11:49:07.827 | [gazebo-1] [Msg] Physics service on [/world/default/set_physics] (async)
go2_ros2    | 2026-05-18 11:49:07.827 | [gazebo-1] [Msg] Physics service on [/world/default/set_physics/blocking] (blocking)
go2_ros2    | 2026-05-18 11:49:07.827 | [gazebo-1] [Msg] SphericalCoordinates service on [/world/default/set_spherical_coordinates] (async)
go2_ros2    | 2026-05-18 11:49:07.827 | [gazebo-1] [Msg] SphericalCoordinates service on [/world/default/set_spherical_coordinates/blocking] (blocking)
go2_ros2    | 2026-05-18 11:49:07.827 | [gazebo-1] [Msg] Enable collision service on [/world/default/enable_collision] (async)
go2_ros2    | 2026-05-18 11:49:07.828 | [gazebo-1] [Msg] Enable collision service on [/world/default/enable_collision/blocking] (blocking)
go2_ros2    | 2026-05-18 11:49:07.828 | [gazebo-1] [Msg] Disable collision service on [/world/default/disable_collision] (async)
go2_ros2    | 2026-05-18 11:49:07.828 | [gazebo-1] [Msg] Disable collision service on [/world/default/disable_collision/blocking] (blocking)
go2_ros2    | 2026-05-18 11:49:07.828 | [gazebo-1] [Msg] Material service on [/world/default/visual_config] (async)
go2_ros2    | 2026-05-18 11:49:07.828 | [gazebo-1] [Msg] Material service on [/world/default/visual_config/blocking] (blocking)
go2_ros2    | 2026-05-18 11:49:07.828 | [gazebo-1] [Msg] Material service on [/world/default/wheel_slip] (async)
go2_ros2    | 2026-05-18 11:49:07.828 | [gazebo-1] [Msg] Material service on [/world/default/wheel_slip/blocking] (blocking)
go2_ros2    | 2026-05-18 11:49:07.828 | [gazebo-1] [Msg] Loaded level [default]
go2_ros2    | 2026-05-18 11:49:07.828 | [gazebo-1] [Msg] Serving world controls on [/world/default/control], [/world/default/control/state] and [/world/default/playback/control]
go2_ros2    | 2026-05-18 11:49:07.828 | [gazebo-1] [Msg] Serving GUI information on [/world/default/gui/info]
go2_ros2    | 2026-05-18 11:49:07.932 | [create-4] [INFO] [1779079747.931139242] [spawn_go2]: Waiting messages on topic [/robot_description].
go2_ros2    | 2026-05-18 11:49:07.950 | [create-4] [INFO] [1779079747.949362704] [spawn_go2]: Entity creation successful.
go2_ros2    | 2026-05-18 11:49:08.010 | [async_slam_toolbox_node-22] [INFO] [1779079748.009754987] [slam_toolbox]: Configuring
go2_ros2    | 2026-05-18 11:49:08.033 | [async_slam_toolbox_node-22] [INFO] [1779079748.032038700] [slam_toolbox]: Using solver plugin solver_plugins::CeresSolver
go2_ros2    | 2026-05-18 11:49:08.038 | [async_slam_toolbox_node-22] [INFO] [1779079748.037432976] [slam_toolbox]: CeresSolver: Using SCHUR_JACOBI preconditioner.
go2_ros2    | 2026-05-18 11:49:08.074 | [lifecycle_manager-33] [INFO] [1779079748.073375507] [lifecycle_manager_navigation]: Starting managed nodes bringup...
go2_ros2    | 2026-05-18 11:49:08.074 | [lifecycle_manager-33] [INFO] [1779079748.073488897] [lifecycle_manager_navigation]: Configuring controller_server
go2_ros2    | 2026-05-18 11:49:08.076 | [controller_server-23] [INFO] [1779079748.074357489] [controller_server]: Configuring controller interface
go2_ros2    | 2026-05-18 11:49:08.076 | [controller_server-23] [INFO] [1779079748.074402950] [controller_server]: getting progress checker plugins..
go2_ros2    | 2026-05-18 11:49:08.076 | [controller_server-23] [INFO] [1779079748.074770134] [controller_server]: getting goal checker plugins..
go2_ros2    | 2026-05-18 11:49:08.076 | [controller_server-23] [INFO] [1779079748.074962920] [controller_server]: Controller frequency set to 3.0000Hz
go2_ros2    | 2026-05-18 11:49:08.076 | [controller_server-23] [INFO] [1779079748.075021844] [local_costmap.local_costmap]: Configuring
go2_ros2    | 2026-05-18 11:49:08.103 | [INFO] [create-4]: process has finished cleanly [pid 74]
go2_ros2    | 2026-05-18 11:49:08.251 | [foxglove_bridge-21] [INFO] [1779079748.251094323] [foxglove_bridge]: Advertising new channel 8 for topic "/waypoint_follower/transition_event"
go2_ros2    | 2026-05-18 11:49:08.252 | [foxglove_bridge-21] [INFO] [1779079748.252320925] [foxglove_bridge]: Advertising new channel 9 for topic "/tf_static"
go2_ros2    | 2026-05-18 11:49:08.253 | [foxglove_bridge-21] [INFO] [1779079748.252678162] [foxglove_bridge]: Advertising new channel 10 for topic "/sim_cmd"
go2_ros2    | 2026-05-18 11:49:08.253 | [foxglove_bridge-21] [INFO] [1779079748.252731719] [foxglove_bridge]: Advertising new channel 11 for topic "/route_server/transition_event"
go2_ros2    | 2026-05-18 11:49:08.253 | [foxglove_bridge-21] [INFO] [1779079748.252903690] [foxglove_bridge]: Advertising new channel 12 for topic "/speech_text"
go2_ros2    | 2026-05-18 11:49:08.253 | [foxglove_bridge-21] [INFO] [1779079748.252917366] [foxglove_bridge]: Advertising new channel 13 for topic "/local_costmap/local_costmap/transition_event"
go2_ros2    | 2026-05-18 11:49:08.253 | [foxglove_bridge-21] [INFO] [1779079748.252924113] [foxglove_bridge]: Advertising new channel 14 for topic "/joint_states"
go2_ros2    | 2026-05-18 11:49:08.253 | [foxglove_bridge-21] [INFO] [1779079748.253081814] [foxglove_bridge]: Advertising new channel 15 for topic "/go2_camera/color/image_raw"
go2_ros2    | 2026-05-18 11:49:08.254 | [foxglove_bridge-21] [INFO] [1779079748.253659301] [foxglove_bridge]: Advertising new channel 16 for topic "/go2_camera/color/camera_info"
go2_ros2    | 2026-05-18 11:49:08.254 | [foxglove_bridge-21] [INFO] [1779079748.253682911] [foxglove_bridge]: Advertising new channel 17 for topic "/go2/robot_description"
go2_ros2    | 2026-05-18 11:49:08.254 | [foxglove_bridge-21] [INFO] [1779079748.253687617] [foxglove_bridge]: Advertising new channel 18 for topic "/robot_description"
go2_ros2    | 2026-05-18 11:49:08.254 | [foxglove_bridge-21] [INFO] [1779079748.254006758] [foxglove_bridge]: Advertising new channel 19 for topic "/go2/robot_velocity"
go2_ros2    | 2026-05-18 11:49:08.254 | [foxglove_bridge-21] [INFO] [1779079748.254346605] [foxglove_bridge]: Advertising new channel 20 for topic "/go2/joint_group_controller/commands"
go2_ros2    | 2026-05-18 11:49:08.254 | [foxglove_bridge-21] [INFO] [1779079748.254467347] [foxglove_bridge]: Advertising new channel 21 for topic "/go2/foot_contact"
go2_ros2    | 2026-05-18 11:49:08.254 | [foxglove_bridge-21] [INFO] [1779079748.254478472] [foxglove_bridge]: Advertising new channel 22 for topic "/go2/color/image_raw"
go2_ros2    | 2026-05-18 11:49:08.254 | [foxglove_bridge-21] [INFO] [1779079748.254484032] [foxglove_bridge]: Advertising new channel 23 for topic "/smoother_server/transition_event"
go2_ros2    | 2026-05-18 11:49:08.256 | [foxglove_bridge-21] [INFO] [1779079748.255734639] [foxglove_bridge]: Advertising new channel 24 for topic "/foot_markers"
go2_ros2    | 2026-05-18 11:49:08.256 | [foxglove_bridge-21] [INFO] [1779079748.255786730] [foxglove_bridge]: Advertising new channel 25 for topic "/controller_server/transition_event"
go2_ros2    | 2026-05-18 11:49:08.256 | [foxglove_bridge-21] [INFO] [1779079748.256353426] [foxglove_bridge]: Advertising new channel 26 for topic "/odom"
go2_ros2    | 2026-05-18 11:49:08.256 | [foxglove_bridge-21] [INFO] [1779079748.256595567] [foxglove_bridge]: Advertising new channel 27 for topic "/go2/color/image_raw/compressed"
go2_ros2    | 2026-05-18 11:49:08.257 | [foxglove_bridge-21] [INFO] [1779079748.256778872] [foxglove_bridge]: Advertising new channel 28 for topic "/cmd_vel_voice"
go2_ros2    | 2026-05-18 11:49:08.257 | [foxglove_bridge-21] [INFO] [1779079748.256809906] [foxglove_bridge]: Advertising new channel 29 for topic "/tf"
go2_ros2    | 2026-05-18 11:49:08.257 | [foxglove_bridge-21] [INFO] [1779079748.257028090] [foxglove_bridge]: Advertising new channel 30 for topic "/go2/imu_plugin/out"
go2_ros2    | 2026-05-18 11:49:08.257 | [foxglove_bridge-21] [INFO] [1779079748.257044193] [foxglove_bridge]: Advertising new channel 31 for topic "/cmd_vel_out"
go2_ros2    | 2026-05-18 11:49:08.257 | [foxglove_bridge-21] [INFO] [1779079748.257049112] [foxglove_bridge]: Advertising new channel 32 for topic "/cmd_vel_joy"
go2_ros2    | 2026-05-18 11:49:08.257 | [foxglove_bridge-21] [INFO] [1779079748.257182517] [foxglove_bridge]: Advertising new channel 33 for topic "/go2/robot_mode"
go2_ros2    | 2026-05-18 11:49:08.257 | [foxglove_bridge-21] [INFO] [1779079748.257196691] [foxglove_bridge]: Advertising new channel 34 for topic "/cmd_vel_foxglove"
go2_ros2    | 2026-05-18 11:49:08.257 | [foxglove_bridge-21] [INFO] [1779079748.257203975] [foxglove_bridge]: Advertising new channel 35 for topic "/cmd_vel"
go2_ros2    | 2026-05-18 11:49:08.258 | [foxglove_bridge-21] [INFO] [1779079748.257456097] [foxglove_bridge]: Advertising new channel 36 for topic "/joy"
go2_ros2    | 2026-05-18 11:49:08.258 | [foxglove_bridge-21] [INFO] [1779079748.257479727] [foxglove_bridge]: Advertising new channel 37 for topic "/bt_navigator/transition_event"
go2_ros2    | 2026-05-18 11:49:08.258 | [foxglove_bridge-21] [INFO] [1779079748.257526033] [foxglove_bridge]: Advertising new channel 38 for topic "/behavior_server/transition_event"
go2_ros2    | 2026-05-18 11:49:08.308 | [parameter_bridge-5] [INFO] [1779079748.307617129] [go2_gz_bridge_clock]: Creating GZ->ROS Bridge: [/clock (gz.msgs.Clock) -> /clock (rosgraph_msgs/msg/Clock)] (Lazy 0)
go2_ros2    | 2026-05-18 11:49:08.407 | [controller_server-23] [INFO] [1779079748.405821095] [local_costmap.local_costmap]: Using plugin "static_layer"
go2_ros2    | 2026-05-18 11:49:08.419 | [controller_server-23] [INFO] [1779079748.418014950] [local_costmap.local_costmap]: Subscribing to the map topic (/map) with transient local durability
go2_ros2    | 2026-05-18 11:49:08.430 | [controller_server-23] [INFO] [1779079748.428074332] [local_costmap.local_costmap]: Initialized plugin "static_layer"
go2_ros2    | 2026-05-18 11:49:08.430 | [controller_server-23] [INFO] [1779079748.428361433] [local_costmap.local_costmap]: Using plugin "voxel_layer"
go2_ros2    | 2026-05-18 11:49:08.437 | [controller_server-23] [INFO] [1779079748.436283647] [local_costmap.local_costmap]: Subscribed to Topics: scan
go2_ros2    | 2026-05-18 11:49:08.470 | [controller_server-23] [INFO] [1779079748.469261982] [local_costmap.local_costmap]: Initialized plugin "voxel_layer"
go2_ros2    | 2026-05-18 11:49:08.470 | [controller_server-23] [INFO] [1779079748.469321726] [local_costmap.local_costmap]: Using plugin "inflation_layer"
go2_ros2    | 2026-05-18 11:49:08.473 | [INFO] [launch.user]: [LifecycleLaunch] Slamtoolbox node is activating.
go2_ros2    | 2026-05-18 11:49:08.478 | [controller_server-23] [INFO] [1779079748.472673691] [local_costmap.local_costmap]: Initialized plugin "inflation_layer"
go2_ros2    | 2026-05-18 11:49:08.479 | [async_slam_toolbox_node-22] [INFO] [1779079748.479034565] [slam_toolbox]: Activating
go2_ros2    | 2026-05-18 11:49:08.547 | [controller_server-23] [INFO] [1779079748.546415317] [controller_server]: Created progress_checker : progress_checker of type nav2_controller::SimpleProgressChecker
go2_ros2    | 2026-05-18 11:49:08.549 | [controller_server-23] [INFO] [1779079748.549278082] [controller_server]: Controller Server has progress_checker  progress checkers available.
go2_ros2    | 2026-05-18 11:49:08.552 | [controller_server-23] [INFO] [1779079748.551102901] [controller_server]: Created goal checker : general_goal_checker of type nav2_controller::SimpleGoalChecker
go2_ros2    | 2026-05-18 11:49:08.555 | [controller_server-23] [INFO] [1779079748.554843881] [controller_server]: Controller Server has general_goal_checker  goal checkers available.
go2_ros2    | 2026-05-18 11:49:08.561 | [controller_server-23] [INFO] [1779079748.560159321] [controller_server]: Created controller : FollowPath of type dwb_core::DWBLocalPlanner
go2_ros2    | 2026-05-18 11:49:08.564 | [controller_server-23] [INFO] [1779079748.563525460] [controller_server]: Setting transform_tolerance to 0.200000
go2_ros2    | 2026-05-18 11:49:08.599 | [controller_server-23] [INFO] [1779079748.599242379] [controller_server]: Using critic "RotateToGoal" (dwb_critics::RotateToGoalCritic)
go2_ros2    | 2026-05-18 11:49:08.602 | [controller_server-23] [INFO] [1779079748.601596716] [controller_server]: Critic plugin initialized
go2_ros2    | 2026-05-18 11:49:08.603 | [controller_server-23] [INFO] [1779079748.601949612] [controller_server]: Using critic "Oscillation" (dwb_critics::OscillationCritic)
go2_ros2    | 2026-05-18 11:49:08.603 | [controller_server-23] [INFO] [1779079748.602973980] [controller_server]: Critic plugin initialized
go2_ros2    | 2026-05-18 11:49:08.604 | [controller_server-23] [INFO] [1779079748.603117327] [controller_server]: Using critic "BaseObstacle" (dwb_critics::BaseObstacleCritic)
go2_ros2    | 2026-05-18 11:49:08.604 | [controller_server-23] [INFO] [1779079748.603510387] [controller_server]: Critic plugin initialized
go2_ros2    | 2026-05-18 11:49:08.604 | [controller_server-23] [INFO] [1779079748.603722696] [controller_server]: Using critic "GoalAlign" (dwb_critics::GoalAlignCritic)
go2_ros2    | 2026-05-18 11:49:08.609 | [controller_server-23] [INFO] [1779079748.607791835] [controller_server]: Critic plugin initialized
go2_ros2    | 2026-05-18 11:49:08.609 | [controller_server-23] [INFO] [1779079748.608076558] [controller_server]: Using critic "PathAlign" (dwb_critics::PathAlignCritic)
go2_ros2    | 2026-05-18 11:49:08.612 | [controller_server-23] [INFO] [1779079748.611409073] [controller_server]: Critic plugin initialized
go2_ros2    | 2026-05-18 11:49:08.613 | [controller_server-23] [INFO] [1779079748.612347045] [controller_server]: Using critic "PathDist" (dwb_critics::PathDistCritic)
go2_ros2    | 2026-05-18 11:49:08.616 | [controller_server-23] [INFO] [1779079748.615342168] [controller_server]: Critic plugin initialized
go2_ros2    | 2026-05-18 11:49:08.616 | [controller_server-23] [INFO] [1779079748.615904042] [controller_server]: Using critic "GoalDist" (dwb_critics::GoalDistCritic)
go2_ros2    | 2026-05-18 11:49:08.618 | [controller_server-23] [INFO] [1779079748.617943787] [controller_server]: Critic plugin initialized
go2_ros2    | 2026-05-18 11:49:08.618 | [controller_server-23] [INFO] [1779079748.618000278] [controller_server]: Controller Server has FollowPath  controllers available.
go2_ros2    | 2026-05-18 11:49:08.646 | [lifecycle_manager-33] [INFO] [1779079748.645609628] [lifecycle_manager_navigation]: Configuring smoother_server
go2_ros2    | 2026-05-18 11:49:08.647 | [smoother_server-24] [INFO] [1779079748.646132725] [smoother_server]: Configuring smoother server
go2_ros2    | 2026-05-18 11:49:08.672 | [smoother_server-24] [INFO] [1779079748.671819996] [smoother_server]: Created smoother : simple_smoother of type nav2_smoother::SimpleSmoother
go2_ros2    | 2026-05-18 11:49:08.674 | [smoother_server-24] [INFO] [1779079748.673551237] [smoother_server]: Smoother Server has simple_smoother  smoothers available.
go2_ros2    | 2026-05-18 11:49:08.692 | [lifecycle_manager-33] [INFO] [1779079748.692010597] [lifecycle_manager_navigation]: Configuring planner_server
go2_ros2    | 2026-05-18 11:49:08.804 | [planner_server-25] [INFO] [1779079748.803792327] [planner_server]: Configuring
go2_ros2    | 2026-05-18 11:49:08.804 | [planner_server-25] [INFO] [1779079748.803861281] [global_costmap.global_costmap]: Configuring
go2_ros2    | 2026-05-18 11:49:08.916 | [gazebo-1] [Msg] World [default] initialized with [default_physics] physics profile.
go2_ros2    | 2026-05-18 11:49:08.916 | [gazebo-1] [Msg] Serving world SDF generation service on [/world/default/generate_world_sdf]
go2_ros2    | 2026-05-18 11:49:08.916 | [gazebo-1] [Msg] Serving world names on [/gazebo/worlds]
go2_ros2    | 2026-05-18 11:49:08.916 | [gazebo-1] [Msg] Resource path add service on [/gazebo/resource_paths/add].
go2_ros2    | 2026-05-18 11:49:08.916 | [gazebo-1] [Msg] Resource path get service on [/gazebo/resource_paths/get].
go2_ros2    | 2026-05-18 11:49:08.916 | [gazebo-1] [Msg] Resource path resolve service on [/gazebo/resource_paths/resolve].
go2_ros2    | 2026-05-18 11:49:08.916 | [gazebo-1] [Msg] Resource paths published on [/gazebo/resource_paths].
go2_ros2    | 2026-05-18 11:49:08.916 | [gazebo-1] [Msg] Server control service on [/server_control].
go2_ros2    | 2026-05-18 11:49:08.916 | [gazebo-1] [Msg] Found no publishers on /stats, adding root stats topic
go2_ros2    | 2026-05-18 11:49:08.916 | [gazebo-1] [Msg] Found no publishers on /clock, adding root clock topic
go2_ros2    | 2026-05-18 11:49:08.929 | [INFO] [gazebo-1]: process has finished cleanly [pid 70]
go2_ros2    | 2026-05-18 11:49:08.930 | [INFO] [launch]: process[gazebo-1] was required: shutting down launched system
go2_ros2    | 2026-05-18 11:49:09.549 | [INFO] [voice_cmd_node-35]: sending signal 'SIGINT' to process[voice_cmd_node-35]
go2_ros2    | 2026-05-18 11:49:09.555 | [INFO] [mic_bridge_node-34]: sending signal 'SIGINT' to process[mic_bridge_node-34]
go2_ros2    | 2026-05-18 11:49:09.566 | [INFO] [lifecycle_manager-33]: sending signal 'SIGINT' to process[lifecycle_manager-33]
go2_ros2    | 2026-05-18 11:49:09.567 | [INFO] [opennav_docking-32]: sending signal 'SIGINT' to process[opennav_docking-32]
go2_ros2    | 2026-05-18 11:49:09.578 | [INFO] [collision_monitor-31]: sending signal 'SIGINT' to process[collision_monitor-31]
go2_ros2    | 2026-05-18 11:49:09.580 | [INFO] [velocity_smoother-30]: sending signal 'SIGINT' to process[velocity_smoother-30]
go2_ros2    | 2026-05-18 11:49:09.591 | [INFO] [waypoint_follower-29]: sending signal 'SIGINT' to process[waypoint_follower-29]
go2_ros2    | 2026-05-18 11:49:09.602 | [INFO] [bt_navigator-28]: sending signal 'SIGINT' to process[bt_navigator-28]
go2_ros2    | 2026-05-18 11:49:09.614 | [INFO] [behavior_server-27]: sending signal 'SIGINT' to process[behavior_server-27]
go2_ros2    | 2026-05-18 11:49:09.627 | [INFO] [route_server-26]: sending signal 'SIGINT' to process[route_server-26]
go2_ros2    | 2026-05-18 11:49:09.639 | [INFO] [planner_server-25]: sending signal 'SIGINT' to process[planner_server-25]
go2_ros2    | 2026-05-18 11:49:09.653 | [INFO] [smoother_server-24]: sending signal 'SIGINT' to process[smoother_server-24]
go2_ros2    | 2026-05-18 11:49:09.669 | [INFO] [controller_server-23]: sending signal 'SIGINT' to process[controller_server-23]
go2_ros2    | 2026-05-18 11:49:09.692 | [INFO] [async_slam_toolbox_node-22]: sending signal 'SIGINT' to process[async_slam_toolbox_node-22]
go2_ros2    | 2026-05-18 11:49:09.706 | [INFO] [foxglove_bridge-21]: sending signal 'SIGINT' to process[foxglove_bridge-21]
go2_ros2    | 2026-05-18 11:49:09.725 | [INFO] [twist_mux-19]: sending signal 'SIGINT' to process[twist_mux-19]
go2_ros2    | 2026-05-18 11:49:09.757 | [INFO] [teleop_node-18]: sending signal 'SIGINT' to process[teleop_node-18]
go2_ros2    | 2026-05-18 11:49:09.775 | [INFO] [joy_node-17]: sending signal 'SIGINT' to process[joy_node-17]
go2_ros2    | 2026-05-18 11:49:09.797 | [INFO] [sim_cmd_node.py-16]: sending signal 'SIGINT' to process[sim_cmd_node.py-16]
go2_ros2    | 2026-05-18 11:49:09.805 | [INFO] [opennav_docking-32]: process has finished cleanly [pid 236]
go2_ros2    | 2026-05-18 11:49:09.818 | [INFO] [relay-15]: sending signal 'SIGINT' to process[relay-15]
go2_ros2    | 2026-05-18 11:49:09.819 | [INFO] [collision_monitor-31]: process has finished cleanly [pid 226]
go2_ros2    | 2026-05-18 11:49:09.820 | [INFO] [velocity_smoother-30]: process has finished cleanly [pid 214]
go2_ros2    | 2026-05-18 11:49:09.831 | [INFO] [relay-14]: sending signal 'SIGINT' to process[relay-14]
go2_ros2    | 2026-05-18 11:49:09.835 | [INFO] [bt_navigator-28]: process has finished cleanly [pid 202]
go2_ros2    | 2026-05-18 11:49:09.847 | [INFO] [relay-13]: sending signal 'SIGINT' to process[relay-13]
go2_ros2    | 2026-05-18 11:49:09.868 | [INFO] [relay-12]: sending signal 'SIGINT' to process[relay-12]
go2_ros2    | 2026-05-18 11:49:09.882 | [INFO] [relay-11]: sending signal 'SIGINT' to process[relay-11]
go2_ros2    | 2026-05-18 11:49:09.896 | [INFO] [QuadrupedOdometryNode.py-10]: sending signal 'SIGINT' to process[QuadrupedOdometryNode.py-10]
go2_ros2    | 2026-05-18 11:49:09.912 | [INFO] [robot_controller_gazebo.py-9]: sending signal 'SIGINT' to process[robot_controller_gazebo.py-9]
go2_ros2    | 2026-05-18 11:49:09.917 | [INFO] [behavior_server-27]: process has finished cleanly [pid 161]
go2_ros2    | 2026-05-18 11:49:09.917 | [INFO] [route_server-26]: process has finished cleanly [pid 147]
go2_ros2    | 2026-05-18 11:49:09.929 | [INFO] [cmd_vel_pub.py-8]: sending signal 'SIGINT' to process[cmd_vel_pub.py-8]
go2_ros2    | 2026-05-18 11:49:09.944 | [INFO] [image_bridge-7]: sending signal 'SIGINT' to process[image_bridge-7]
go2_ros2    | 2026-05-18 11:49:09.949 | [ERROR] [voice_cmd_node-35]: process has died [pid 243, exit code 1, cmd '/ros2_ws/install/speech_processor/lib/speech_processor/voice_cmd_node --ros-args -r __node:=voice_cmd_node --params-file /tmp/launch_params_mp9hbtaw'].
go2_ros2    | 2026-05-18 11:49:09.961 | [INFO] [parameter_bridge-6]: sending signal 'SIGINT' to process[parameter_bridge-6]
go2_ros2    | 2026-05-18 11:49:09.992 | [INFO] [parameter_bridge-5]: sending signal 'SIGINT' to process[parameter_bridge-5]
go2_ros2    | 2026-05-18 11:49:10.010 | [INFO] [robot_state_publisher-3]: sending signal 'SIGINT' to process[robot_state_publisher-3]
go2_ros2    | 2026-05-18 11:49:10.010 | [INFO] [teleop_node-18]: process has finished cleanly [pid 90]
go2_ros2    | 2026-05-18 11:49:10.025 | [INFO] [robot_state_publisher-2]: sending signal 'SIGINT' to process[robot_state_publisher-2]
go2_ros2    | 2026-05-18 11:49:10.027 | [ERROR] [mic_bridge_node-34]: process has died [pid 241, exit code 1, cmd '/ros2_ws/install/speech_processor/lib/speech_processor/mic_bridge_node --ros-args -r __node:=mic_bridge_node --params-file /tmp/launch_params_q0iq2qj8'].
go2_ros2    | 2026-05-18 11:49:10.027 | [planner_server-25] [INFO] [1779079748.946180935] [global_costmap.global_costmap]: Using plugin "static_layer"
go2_ros2    | 2026-05-18 11:49:10.028 | [planner_server-25] [INFO] [1779079748.951003334] [global_costmap.global_costmap]: Subscribing to the map topic (/map) with transient local durability
go2_ros2    | 2026-05-18 11:49:10.028 | [planner_server-25] [INFO] [1779079748.954421786] [global_costmap.global_costmap]: Initialized plugin "static_layer"
go2_ros2    | 2026-05-18 11:49:10.028 | [planner_server-25] [INFO] [1779079748.954456898] [global_costmap.global_costmap]: Using plugin "voxel_layer"
go2_ros2    | 2026-05-18 11:49:10.028 | [planner_server-25] [INFO] [1779079748.956336094] [global_costmap.global_costmap]: Subscribed to Topics: scan
go2_ros2    | 2026-05-18 11:49:10.028 | [planner_server-25] [INFO] [1779079749.306234291] [global_costmap.global_costmap]: Initialized plugin "voxel_layer"
go2_ros2    | 2026-05-18 11:49:10.028 | [planner_server-25] [INFO] [1779079749.306287619] [global_costmap.global_costmap]: Using plugin "inflation_layer"
go2_ros2    | 2026-05-18 11:49:10.028 | [planner_server-25] [INFO] [1779079749.318133571] [global_costmap.global_costmap]: Initialized plugin "inflation_layer"
go2_ros2    | 2026-05-18 11:49:10.028 | [planner_server-25] [INFO] [1779079749.375237244] [planner_server]: Created global planner plugin GridBased of type nav2_smac_planner::SmacPlannerHybrid
go2_ros2    | 2026-05-18 11:49:10.028 | [planner_server-25] [INFO] [1779079749.375285469] [planner_server]: Configuring GridBased of type SmacPlannerHybrid
go2_ros2    | 2026-05-18 11:49:10.028 | [planner_server-25] [INFO] [1779079749.389313312] [planner_server]: Even sized heuristic lookup table size set 400.000000, increasing size by 1 to make odd
go2_ros2    | 2026-05-18 11:49:10.029 | [INFO] [twist_mux-19]: process has finished cleanly [pid 91]
go2_ros2    | 2026-05-18 11:49:10.029 | [foxglove_bridge-21] [INFO] [1779079749.179862007] [foxglove_bridge]: Advertising new channel 39 for topic "/slam_toolbox/scan_visualization"
go2_ros2    | 2026-05-18 11:49:10.029 | [foxglove_bridge-21] [INFO] [1779079749.179939393] [foxglove_bridge]: Advertising new channel 40 for topic "/slam_toolbox/graph_visualization"
go2_ros2    | 2026-05-18 11:49:10.029 | [foxglove_bridge-21] [INFO] [1779079749.180142948] [foxglove_bridge]: Advertising new channel 41 for topic "/pose"
go2_ros2    | 2026-05-18 11:49:10.029 | [foxglove_bridge-21] [INFO] [1779079749.180376677] [foxglove_bridge]: Advertising new channel 42 for topic "/received_global_plan"
go2_ros2    | 2026-05-18 11:49:10.029 | [foxglove_bridge-21] [INFO] [1779079749.181064314] [foxglove_bridge]: Advertising new channel 43 for topic "/slam_toolbox/update"
go2_ros2    | 2026-05-18 11:49:10.029 | [foxglove_bridge-21] [INFO] [1779079749.181084142] [foxglove_bridge]: Advertising new channel 44 for topic "/plan_smoothed"
go2_ros2    | 2026-05-18 11:49:10.029 | [foxglove_bridge-21] [INFO] [1779079749.181328950] [foxglove_bridge]: Advertising new channel 45 for topic "/map"
go2_ros2    | 2026-05-18 11:49:10.029 | [foxglove_bridge-21] [INFO] [1779079749.181342679] [foxglove_bridge]: Advertising new channel 46 for topic "/local_plan"
go2_ros2    | 2026-05-18 11:49:10.030 | [foxglove_bridge-21] [INFO] [1779079749.181515954] [foxglove_bridge]: Advertising new channel 47 for topic "/local_costmap/voxel_layer_updates"
go2_ros2    | 2026-05-18 11:49:10.030 | [foxglove_bridge-21] [INFO] [1779079749.181680065] [foxglove_bridge]: Advertising new channel 48 for topic "/slam_toolbox/feedback"
go2_ros2    | 2026-05-18 11:49:10.031 | [foxglove_bridge-21] [INFO] [1779079749.181805901] [foxglove_bridge]: Advertising new channel 49 for topic "/local_costmap/voxel_layer_raw_updates"
go2_ros2    | 2026-05-18 11:49:10.031 | [foxglove_bridge-21] [INFO] [1779079749.182068347] [foxglove_bridge]: Advertising new channel 50 for topic "/local_costmap/voxel_layer_raw"
go2_ros2    | 2026-05-18 11:49:10.031 | [foxglove_bridge-21] [INFO] [1779079749.182082127] [foxglove_bridge]: Advertising new channel 51 for topic "/local_costmap/voxel_layer"
go2_ros2    | 2026-05-18 11:49:10.031 | [foxglove_bridge-21] [INFO] [1779079749.182086734] [foxglove_bridge]: Advertising new channel 52 for topic "/local_costmap/static_layer_updates"
go2_ros2    | 2026-05-18 11:49:10.031 | [foxglove_bridge-21] [INFO] [1779079749.182090995] [foxglove_bridge]: Advertising new channel 53 for topic "/transformed_global_plan"
go2_ros2    | 2026-05-18 11:49:10.031 | [foxglove_bridge-21] [INFO] [1779079749.182095006] [foxglove_bridge]: Advertising new channel 54 for topic "/local_costmap/static_layer_raw_updates"
go2_ros2    | 2026-05-18 11:49:10.031 | [foxglove_bridge-21] [INFO] [1779079749.182185803] [foxglove_bridge]: Advertising new channel 55 for topic "/map_metadata"
go2_ros2    | 2026-05-18 11:49:10.031 | [foxglove_bridge-21] [INFO] [1779079749.182190843] [foxglove_bridge]: Advertising new channel 56 for topic "/local_costmap/static_layer"
go2_ros2    | 2026-05-18 11:49:10.031 | [foxglove_bridge-21] [INFO] [1779079749.182428667] [foxglove_bridge]: Advertising new channel 57 for topic "/local_costmap/voxel_grid"
go2_ros2    | 2026-05-18 11:49:10.031 | [foxglove_bridge-21] [INFO] [1779079749.182542935] [foxglove_bridge]: Advertising new channel 58 for topic "/local_costmap/footprint"
go2_ros2    | 2026-05-18 11:49:10.031 | [foxglove_bridge-21] [INFO] [1779079749.182548700] [foxglove_bridge]: Advertising new channel 59 for topic "/local_costmap/costmap_raw"
go2_ros2    | 2026-05-18 11:49:10.031 | [foxglove_bridge-21] [INFO] [1779079749.182656140] [foxglove_bridge]: Advertising new channel 60 for topic "/speed_limit"
go2_ros2    | 2026-05-18 11:49:10.032 | [foxglove_bridge-21] [INFO] [1779079749.182861814] [foxglove_bridge]: Advertising new channel 61 for topic "/local_costmap/clearing_endpoints"
go2_ros2    | 2026-05-18 11:49:10.032 | [foxglove_bridge-21] [INFO] [1779079749.183095009] [foxglove_bridge]: Advertising new channel 62 for topic "/local_costmap/published_footprint"
go2_ros2    | 2026-05-18 11:49:10.032 | [foxglove_bridge-21] [INFO] [1779079749.183109076] [foxglove_bridge]: Advertising new channel 63 for topic "/go2/color/camera_info"
go2_ros2    | 2026-05-18 11:49:10.032 | [foxglove_bridge-21] [INFO] [1779079749.183113680] [foxglove_bridge]: Advertising new channel 64 for topic "/global_costmap/published_footprint"
go2_ros2    | 2026-05-18 11:49:10.032 | [foxglove_bridge-21] [INFO] [1779079749.183124430] [foxglove_bridge]: Advertising new channel 65 for topic "/global_costmap/costmap_raw"
go2_ros2    | 2026-05-18 11:49:10.032 | [foxglove_bridge-21] [INFO] [1779079749.183128768] [foxglove_bridge]: Advertising new channel 66 for topic "/global_costmap/costmap_raw_updates"
go2_ros2    | 2026-05-18 11:49:10.032 | [foxglove_bridge-21] [INFO] [1779079749.183138371] [foxglove_bridge]: Advertising new channel 67 for topic "/cost_cloud"
go2_ros2    | 2026-05-18 11:49:10.032 | [foxglove_bridge-21] [INFO] [1779079749.183148609] [foxglove_bridge]: Advertising new channel 68 for topic "/marker"
go2_ros2    | 2026-05-18 11:49:10.032 | [foxglove_bridge-21] [INFO] [1779079749.183155779] [foxglove_bridge]: Advertising new channel 69 for topic "/local_costmap/static_layer_raw"
go2_ros2    | 2026-05-18 11:49:10.032 | [foxglove_bridge-21] [INFO] [1779079749.183160259] [foxglove_bridge]: Advertising new channel 70 for topic "/local_costmap/costmap_raw_updates"
go2_ros2    | 2026-05-18 11:49:10.032 | [foxglove_bridge-21] [INFO] [1779079749.183168612] [foxglove_bridge]: Advertising new channel 71 for topic "/local_costmap/costmap"
go2_ros2    | 2026-05-18 11:49:10.032 | [foxglove_bridge-21] [INFO] [1779079749.183776823] [foxglove_bridge]: Advertising new channel 72 for topic "/evaluation"
go2_ros2    | 2026-05-18 11:49:10.032 | [foxglove_bridge-21] [INFO] [1779079749.183792902] [foxglove_bridge]: Advertising new channel 73 for topic "/cmd_vel_nav"
go2_ros2    | 2026-05-18 11:49:10.032 | [foxglove_bridge-21] [INFO] [1779079749.183824559] [foxglove_bridge]: Advertising new channel 74 for topic "/local_costmap/costmap_updates"
go2_ros2    | 2026-05-18 11:49:10.032 | [foxglove_bridge-21] [INFO] [1779079749.183830273] [foxglove_bridge]: Advertising new channel 75 for topic "/scan"
go2_ros2    | 2026-05-18 11:49:10.032 | [lifecycle_manager-33] [INFO] [1779079749.561160981] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:49:10.032 | [lifecycle_manager-33] [INFO] [1779079749.561266138] [lifecycle_manager_navigation]: Running Nav2 LifecycleManager rcl preshutdown (lifecycle_manager_navigation)
go2_ros2    | 2026-05-18 11:49:10.035 | [opennav_docking-32] [INFO] [1779079749.567668389] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:49:10.035 | [opennav_docking-32] [INFO] [1779079749.567784514] [docking_server]: Running Nav2 LifecycleNode rcl preshutdown (docking_server)
go2_ros2    | 2026-05-18 11:49:10.035 | [opennav_docking-32] [INFO] [1779079749.567841160] [docking_server]: Destroying bond (docking_server) to lifecycle manager.
go2_ros2    | 2026-05-18 11:49:10.035 | [opennav_docking-32] [INFO] [1779079749.572252459] [docking_server]: Destroying
go2_ros2    | 2026-05-18 11:49:10.036 | [collision_monitor-31] [INFO] [1779079749.575029667] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:49:10.038 | [collision_monitor-31] [INFO] [1779079749.575292713] [collision_monitor]: Running Nav2 LifecycleNode rcl preshutdown (collision_monitor)
go2_ros2    | 2026-05-18 11:49:10.040 | [collision_monitor-31] [INFO] [1779079749.575336449] [collision_monitor]: Destroying bond (collision_monitor) to lifecycle manager.
go2_ros2    | 2026-05-18 11:49:10.043 | [velocity_smoother-30] [INFO] [1779079749.580496599] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:49:10.043 | [velocity_smoother-30] [INFO] [1779079749.580697676] [velocity_smoother]: Running Nav2 LifecycleNode rcl preshutdown (velocity_smoother)
go2_ros2    | 2026-05-18 11:49:10.043 | [velocity_smoother-30] [INFO] [1779079749.580800817] [velocity_smoother]: Destroying bond (velocity_smoother) to lifecycle manager.
go2_ros2    | 2026-05-18 11:49:10.043 | [velocity_smoother-30] [INFO] [1779079749.585969256] [velocity_smoother]: Destroying
go2_ros2    | 2026-05-18 11:49:10.045 | [collision_monitor-31] [INFO] [1779079749.582519799] [collision_monitor]: Destroying
go2_ros2    | 2026-05-18 11:49:10.045 | [waypoint_follower-29] [INFO] [1779079749.592906471] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:49:10.050 | [waypoint_follower-29] [INFO] [1779079749.593017950] [waypoint_follower]: Running Nav2 LifecycleNode rcl preshutdown (waypoint_follower)
go2_ros2    | 2026-05-18 11:49:10.050 | [waypoint_follower-29] [INFO] [1779079749.593069889] [waypoint_follower]: Destroying bond (waypoint_follower) to lifecycle manager.
go2_ros2    | 2026-05-18 11:49:10.050 | [bt_navigator-28] [INFO] [1779079749.602701937] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:49:10.050 | [bt_navigator-28] [INFO] [1779079749.602826438] [bt_navigator]: Running Nav2 LifecycleNode rcl preshutdown (bt_navigator)
go2_ros2    | 2026-05-18 11:49:10.050 | [bt_navigator-28] [INFO] [1779079749.602896610] [bt_navigator]: Destroying bond (bt_navigator) to lifecycle manager.
go2_ros2    | 2026-05-18 11:49:10.050 | [bt_navigator-28] [INFO] [1779079749.604806414] [bt_navigator]: Destroying
go2_ros2    | 2026-05-18 11:49:10.050 | [INFO] [joy_node-17]: process has finished cleanly [pid 87]
go2_ros2    | 2026-05-18 11:49:10.050 | [voice_cmd_node-35] Traceback (most recent call last):
go2_ros2    | 2026-05-18 11:49:10.050 | [voice_cmd_node-35]   File "/ros2_ws/install/speech_processor/lib/speech_processor/voice_cmd_node", line 33, in <module>
go2_ros2    | 2026-05-18 11:49:10.050 | [voice_cmd_node-35]     sys.exit(load_entry_point('speech-processor==1.0.0', 'console_scripts', 'voice_cmd_node')())
go2_ros2    | 2026-05-18 11:49:10.050 | [voice_cmd_node-35]              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
go2_ros2    | 2026-05-18 11:49:10.050 | [voice_cmd_node-35]   File "/ros2_ws/install/speech_processor/lib/python3.12/site-packages/speech_processor/voice_cmd_node.py", line 501, in main
go2_ros2    | 2026-05-18 11:49:10.050 | [voice_cmd_node-35]     rclpy.shutdown()
go2_ros2    | 2026-05-18 11:49:10.050 | [voice_cmd_node-35]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/__init__.py", line 134, in shutdown
go2_ros2    | 2026-05-18 11:49:10.050 | [voice_cmd_node-35]     _shutdown(context=context)
go2_ros2    | 2026-05-18 11:49:10.050 | [voice_cmd_node-35]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/utilities.py", line 82, in shutdown
go2_ros2    | 2026-05-18 11:49:10.050 | [voice_cmd_node-35]     context.shutdown()
go2_ros2    | 2026-05-18 11:49:10.050 | [voice_cmd_node-35]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/context.py", line 129, in shutdown
go2_ros2    | 2026-05-18 11:49:10.050 | [voice_cmd_node-35]     self.__context.shutdown()
go2_ros2    | 2026-05-18 11:49:10.050 | [voice_cmd_node-35] rclpy._rclpy_pybind11.RCLError: failed to shutdown: rcl_shutdown already called on the given context, at ./src/rcl/init.c:333
go2_ros2    | 2026-05-18 11:49:10.050 | [behavior_server-27] [INFO] [1779079749.614707635] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:49:10.050 | [behavior_server-27] [INFO] [1779079749.615033485] [behavior_server]: Running Nav2 LifecycleNode rcl preshutdown (behavior_server)
go2_ros2    | 2026-05-18 11:49:10.050 | [behavior_server-27] [INFO] [1779079749.615089463] [behavior_server]: Destroying bond (behavior_server) to lifecycle manager.
go2_ros2    | 2026-05-18 11:49:10.050 | [behavior_server-27] [INFO] [1779079749.619064330] [behavior_server]: Destroying
go2_ros2    | 2026-05-18 11:49:10.050 | [mic_bridge_node-34] Traceback (most recent call last):
go2_ros2    | 2026-05-18 11:49:10.051 | [mic_bridge_node-34]   File "/ros2_ws/install/speech_processor/lib/speech_processor/mic_bridge_node", line 33, in <module>
go2_ros2    | 2026-05-18 11:49:10.051 | [mic_bridge_node-34]     sys.exit(load_entry_point('speech-processor==1.0.0', 'console_scripts', 'mic_bridge_node')())
go2_ros2    | 2026-05-18 11:49:10.051 | [mic_bridge_node-34]              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
go2_ros2    | 2026-05-18 11:49:10.051 | [mic_bridge_node-34]   File "/ros2_ws/install/speech_processor/lib/python3.12/site-packages/speech_processor/mic_bridge_node.py", line 522, in main
go2_ros2    | 2026-05-18 11:49:10.051 | [mic_bridge_node-34]     rclpy.shutdown()
go2_ros2    | 2026-05-18 11:49:10.051 | [mic_bridge_node-34]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/__init__.py", line 134, in shutdown
go2_ros2    | 2026-05-18 11:49:10.051 | [mic_bridge_node-34]     _shutdown(context=context)
go2_ros2    | 2026-05-18 11:49:10.051 | [mic_bridge_node-34]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/utilities.py", line 82, in shutdown
go2_ros2    | 2026-05-18 11:49:10.051 | [mic_bridge_node-34]     context.shutdown()
go2_ros2    | 2026-05-18 11:49:10.051 | [mic_bridge_node-34]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/context.py", line 129, in shutdown
go2_ros2    | 2026-05-18 11:49:10.051 | [mic_bridge_node-34]     self.__context.shutdown()
go2_ros2    | 2026-05-18 11:49:10.051 | [mic_bridge_node-34] rclpy._rclpy_pybind11.RCLError: failed to shutdown: rcl_shutdown already called on the given context, at ./src/rcl/init.c:333
go2_ros2    | 2026-05-18 11:49:10.051 | [INFO] [smoother_server-24]: process has finished cleanly [pid 132]
go2_ros2    | 2026-05-18 11:49:10.053 | [route_server-26] [INFO] [1779079749.627634863] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:49:10.053 | [route_server-26] [INFO] [1779079749.627916810] [route_server]: Running Nav2 LifecycleNode rcl preshutdown (route_server)
go2_ros2    | 2026-05-18 11:49:10.053 | [route_server-26] [INFO] [1779079749.627991938] [route_server]: Destroying bond (route_server) to lifecycle manager.
go2_ros2    | 2026-05-18 11:49:10.058 | [route_server-26] [INFO] [1779079749.634909176] [route_server]: Destroying
go2_ros2    | 2026-05-18 11:49:10.058 | [planner_server-25] [INFO] [1779079749.640761350] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:49:10.058 | [planner_server-25] [INFO] [1779079749.641170383] [planner_server]: Running Nav2 LifecycleNode rcl preshutdown (planner_server)
go2_ros2    | 2026-05-18 11:49:10.058 | [planner_server-25] [INFO] [1779079749.641300750] [planner_server]: Destroying bond (planner_server) to lifecycle manager.
go2_ros2    | 2026-05-18 11:49:10.058 | [smoother_server-24] [INFO] [1779079749.657955005] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:49:10.058 | [smoother_server-24] [INFO] [1779079749.658143622] [smoother_server]: Running Nav2 LifecycleNode rcl preshutdown (smoother_server)
go2_ros2    | 2026-05-18 11:49:10.058 | [smoother_server-24] [INFO] [1779079749.658275037] [smoother_server]: Cleaning up
go2_ros2    | 2026-05-18 11:49:10.058 | [controller_server-23] [INFO] [1779079749.669766468] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:49:10.058 | [controller_server-23] [INFO] [1779079749.670488590] [controller_server]: Running Nav2 LifecycleNode rcl preshutdown (controller_server)
go2_ros2    | 2026-05-18 11:49:10.058 | [controller_server-23] [INFO] [1779079749.670647636] [controller_server]: Cleaning up
go2_ros2    | 2026-05-18 11:49:10.058 | [controller_server-23] [INFO] [1779079749.671112335] [local_costmap.local_costmap]: Cleaning up
go2_ros2    | 2026-05-18 11:49:10.058 | [async_slam_toolbox_node-22] [INFO] [1779079749.690386691] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:49:10.058 | [foxglove_bridge-21] [INFO] [1779079749.709625544] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:49:10.059 | [foxglove_bridge-21] [INFO] [1779079749.719617659] [foxglove_bridge]: Shutting down foxglove_bridge
go2_ros2    | 2026-05-18 11:49:10.060 | [twist_mux-19] [INFO] [1779079749.726840843] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:49:10.061 | [smoother_server-24] [INFO] [1779079749.744124120] [smoother_server]: Destroying bond (smoother_server) to lifecycle manager.
go2_ros2    | 2026-05-18 11:49:10.062 | [foxglove_bridge-21] [INFO] [1779079749.754654548] [foxglove_bridge]: Shutdown complete
go2_ros2    | 2026-05-18 11:49:10.064 | [teleop_node-18] [INFO] [1779079749.757545124] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:49:10.064 | [joy_node-17] [INFO] [1779079749.776304002] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:49:10.066 | [INFO] [relay-14]: process has finished cleanly [pid 84]
go2_ros2    | 2026-05-18 11:49:10.067 | [smoother_server-24] [INFO] [1779079749.798404639] [smoother_server]: Destroying
go2_ros2    | 2026-05-18 11:49:10.069 | [relay-15] [INFO] [1779079749.815281845] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:49:10.070 | [relay-14] [INFO] [1779079749.830785098] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:49:10.070 | [relay-13] [INFO] [1779079749.847086304] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:49:10.071 | [waypoint_follower-29] [INFO] [1779079749.847997116] [waypoint_follower]: Destroying
go2_ros2    | 2026-05-18 11:49:10.072 | [relay-12] [INFO] [1779079749.872915303] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:49:10.073 | [relay-11] [INFO] [1779079749.885408341] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:49:10.073 | [INFO] [relay-12]: process has finished cleanly [pid 82]
go2_ros2    | 2026-05-18 11:49:10.075 | [robot_controller_gazebo.py-9] Traceback (most recent call last):
go2_ros2    | 2026-05-18 11:49:10.075 | [robot_controller_gazebo.py-9]   File "/ros2_ws/install/go2_sim/lib/go2_sim/robot_controller_gazebo.py", line 77, in <module>
go2_ros2    | 2026-05-18 11:49:10.076 | [robot_controller_gazebo.py-9]     main()
go2_ros2    | 2026-05-18 11:49:10.076 | [robot_controller_gazebo.py-9]   File "/ros2_ws/install/go2_sim/lib/go2_sim/robot_controller_gazebo.py", line 72, in main
go2_ros2    | 2026-05-18 11:49:10.076 | [robot_controller_gazebo.py-9]     rclpy.spin(node)
go2_ros2    | 2026-05-18 11:49:10.076 | [robot_controller_gazebo.py-9]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/__init__.py", line 247, in spin
go2_ros2    | 2026-05-18 11:49:10.077 | [robot_controller_gazebo.py-9]     executor.spin_once()
go2_ros2    | 2026-05-18 11:49:10.077 | [robot_controller_gazebo.py-9]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/executors.py", line 926, in spin_once
go2_ros2    | 2026-05-18 11:49:10.077 | [robot_controller_gazebo.py-9]     self._spin_once_impl(timeout_sec)
go2_ros2    | 2026-05-18 11:49:10.077 | [robot_controller_gazebo.py-9]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/executors.py", line 907, in _spin_once_impl
go2_ros2    | 2026-05-18 11:49:10.078 | [robot_controller_gazebo.py-9]     handler, entity, node = self.wait_for_ready_callbacks(
go2_ros2    | 2026-05-18 11:49:10.078 | [robot_controller_gazebo.py-9]                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
go2_ros2    | 2026-05-18 11:49:10.079 | [robot_controller_gazebo.py-9]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/executors.py", line 877, in wait_for_ready_callbacks
go2_ros2    | 2026-05-18 11:49:10.079 | [robot_controller_gazebo.py-9]     return next(self._cb_iter)
go2_ros2    | 2026-05-18 11:49:10.079 | [robot_controller_gazebo.py-9]            ^^^^^^^^^^^^^^^^^^^
go2_ros2    | 2026-05-18 11:49:10.079 | [robot_controller_gazebo.py-9]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/executors.py", line 781, in _wait_for_ready_callbacks
go2_ros2    | 2026-05-18 11:49:10.079 | [robot_controller_gazebo.py-9]     wait_set.wait(timeout_nsec)
go2_ros2    | 2026-05-18 11:49:10.079 | [robot_controller_gazebo.py-9] KeyboardInterrupt
go2_ros2    | 2026-05-18 11:49:10.080 | [sim_cmd_node.py-16] Traceback (most recent call last):
go2_ros2    | 2026-05-18 11:49:10.080 | [sim_cmd_node.py-16]   File "/ros2_ws/install/go2_sim/lib/go2_sim/sim_cmd_node.py", line 185, in <module>
go2_ros2    | 2026-05-18 11:49:10.080 | [sim_cmd_node.py-16]     main()
go2_ros2    | 2026-05-18 11:49:10.080 | [sim_cmd_node.py-16]   File "/ros2_ws/install/go2_sim/lib/go2_sim/sim_cmd_node.py", line 181, in main
go2_ros2    | 2026-05-18 11:49:10.080 | [sim_cmd_node.py-16]     rclpy.shutdown()
go2_ros2    | 2026-05-18 11:49:10.080 | [sim_cmd_node.py-16]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/__init__.py", line 134, in shutdown
go2_ros2    | 2026-05-18 11:49:10.080 | [sim_cmd_node.py-16]     _shutdown(context=context)
go2_ros2    | 2026-05-18 11:49:10.081 | [sim_cmd_node.py-16]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/utilities.py", line 82, in shutdown
go2_ros2    | 2026-05-18 11:49:10.081 | [sim_cmd_node.py-16]     context.shutdown()
go2_ros2    | 2026-05-18 11:49:10.082 | [sim_cmd_node.py-16]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/context.py", line 129, in shutdown
go2_ros2    | 2026-05-18 11:49:10.083 | [INFO] [relay-15]: process has finished cleanly [pid 85]
go2_ros2    | 2026-05-18 11:49:10.084 | [sim_cmd_node.py-16]     self.__context.shutdown()
go2_ros2    | 2026-05-18 11:49:10.084 | [sim_cmd_node.py-16] rclpy._rclpy_pybind11.RCLError: failed to shutdown: rcl_shutdown already called on the given context, at ./src/rcl/init.c:333
go2_ros2    | 2026-05-18 11:49:10.086 | [image_bridge-7] [INFO] [1779079749.944608836] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:49:10.086 | [INFO] [relay-13]: process has finished cleanly [pid 83]
go2_ros2    | 2026-05-18 11:49:10.087 | [controller_server-23] [INFO] [1779079749.957693621] [controller_server]: Destroying bond (controller_server) to lifecycle manager.
go2_ros2    | 2026-05-18 11:49:10.088 | [parameter_bridge-6] [INFO] [1779079749.961817299] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:49:10.088 | [parameter_bridge-5] [INFO] [1779079749.988537039] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:49:10.090 | [robot_state_publisher-3] [INFO] [1779079750.008731223] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:49:10.091 | [QuadrupedOdometryNode.py-10] Traceback (most recent call last):
go2_ros2    | 2026-05-18 11:49:10.091 | [QuadrupedOdometryNode.py-10]   File "/ros2_ws/install/go2_sim/lib/go2_sim/QuadrupedOdometryNode.py", line 470, in <module>
go2_ros2    | 2026-05-18 11:49:10.091 | [QuadrupedOdometryNode.py-10]     main()
go2_ros2    | 2026-05-18 11:49:10.091 | [QuadrupedOdometryNode.py-10]   File "/ros2_ws/install/go2_sim/lib/go2_sim/QuadrupedOdometryNode.py", line 467, in main
go2_ros2    | 2026-05-18 11:49:10.091 | [QuadrupedOdometryNode.py-10]     rclpy.shutdown()
go2_ros2    | 2026-05-18 11:49:10.091 | [QuadrupedOdometryNode.py-10]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/__init__.py", line 134, in shutdown
go2_ros2    | 2026-05-18 11:49:10.091 | [QuadrupedOdometryNode.py-10]     _shutdown(context=context)
go2_ros2    | 2026-05-18 11:49:10.091 | [QuadrupedOdometryNode.py-10]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/utilities.py", line 82, in shutdown
go2_ros2    | 2026-05-18 11:49:10.091 | [QuadrupedOdometryNode.py-10]     context.shutdown()
go2_ros2    | 2026-05-18 11:49:10.091 | [QuadrupedOdometryNode.py-10]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/context.py", line 129, in shutdown
go2_ros2    | 2026-05-18 11:49:10.091 | [QuadrupedOdometryNode.py-10]     self.__context.shutdown()
go2_ros2    | 2026-05-18 11:49:10.092 | [QuadrupedOdometryNode.py-10] rclpy._rclpy_pybind11.RCLError: failed to shutdown: rcl_shutdown already called on the given context, at ./src/rcl/init.c:333
go2_ros2    | 2026-05-18 11:49:10.094 | [controller_server-23] [INFO] [1779079750.012819031] [local_costmap.local_costmap]: Destroying
go2_ros2    | 2026-05-18 11:49:10.095 | [cmd_vel_pub.py-8] Traceback (most recent call last):
go2_ros2    | 2026-05-18 11:49:10.095 | [cmd_vel_pub.py-8]   File "/ros2_ws/install/go2_sim/lib/go2_sim/cmd_vel_pub.py", line 115, in <module>
go2_ros2    | 2026-05-18 11:49:10.095 | [cmd_vel_pub.py-8]     main()
go2_ros2    | 2026-05-18 11:49:10.095 | [cmd_vel_pub.py-8]   File "/ros2_ws/install/go2_sim/lib/go2_sim/cmd_vel_pub.py", line 112, in main
go2_ros2    | 2026-05-18 11:49:10.095 | [cmd_vel_pub.py-8]     rclpy.shutdown()
go2_ros2    | 2026-05-18 11:49:10.095 | [cmd_vel_pub.py-8]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/__init__.py", line 134, in shutdown
go2_ros2    | 2026-05-18 11:49:10.095 | [cmd_vel_pub.py-8]     _shutdown(context=context)
go2_ros2    | 2026-05-18 11:49:10.095 | [cmd_vel_pub.py-8]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/utilities.py", line 82, in shutdown
go2_ros2    | 2026-05-18 11:49:10.096 | [cmd_vel_pub.py-8]     context.shutdown()
go2_ros2    | 2026-05-18 11:49:10.096 | [cmd_vel_pub.py-8]   File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/context.py", line 129, in shutdown
go2_ros2    | 2026-05-18 11:49:10.097 | [cmd_vel_pub.py-8]     self.__context.shutdown()
go2_ros2    | 2026-05-18 11:49:10.097 | [cmd_vel_pub.py-8] rclpy._rclpy_pybind11.RCLError: failed to shutdown: rcl_shutdown already called on the given context, at ./src/rcl/init.c:333
go2_ros2    | 2026-05-18 11:49:10.098 | [robot_state_publisher-2] [INFO] [1779079750.026513462] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2    | 2026-05-18 11:49:10.100 | [controller_server-23] [INFO] [1779079750.060588303] [controller_server]: Destroying
go2_ros2    | 2026-05-18 11:49:10.108 | [ERROR] [robot_controller_gazebo.py-9]: process has died [pid 79, exit code -2, cmd '/ros2_ws/install/go2_sim/lib/go2_sim/robot_controller_gazebo.py --ros-args -r __node:=quadruped_controller -r __ns:=/go2 --params-file /tmp/launch_params_ox2tqlsg'].
go2_ros2    | 2026-05-18 11:49:10.112 | [INFO] [waypoint_follower-29]: process has finished cleanly [pid 206]
go2_ros2    | 2026-05-18 11:49:10.118 | [INFO] [parameter_bridge-6]: process has finished cleanly [pid 76]
go2_ros2    | 2026-05-18 11:49:10.128 | [INFO] [relay-11]: process has finished cleanly [pid 81]
go2_ros2    | 2026-05-18 11:49:10.132 | [INFO] [parameter_bridge-5]: process has finished cleanly [pid 75]
go2_ros2    | 2026-05-18 11:49:10.142 | [ERROR] [sim_cmd_node.py-16]: process has died [pid 86, exit code 1, cmd '/ros2_ws/install/go2_sim/lib/go2_sim/sim_cmd_node.py --ros-args -r __node:=sim_cmd_node --params-file /tmp/launch_params_y0v658yg'].
go2_ros2    | 2026-05-18 11:49:10.142 | [INFO] [async_slam_toolbox_node-22]: process has finished cleanly [pid 120]
go2_ros2    | 2026-05-18 11:49:10.143 | [INFO] [image_bridge-7]: process has finished cleanly [pid 77]
go2_ros2    | 2026-05-18 11:49:10.170 | [INFO] [robot_state_publisher-3]: process has finished cleanly [pid 73]
go2_ros2    | 2026-05-18 11:49:10.182 | [INFO] [robot_state_publisher-2]: process has finished cleanly [pid 71]
go2_ros2    | 2026-05-18 11:49:10.209 | [INFO] [controller_server-23]: process has finished cleanly [pid 128]
go2_ros2    | 2026-05-18 11:49:10.218 | [ERROR] [cmd_vel_pub.py-8]: process has died [pid 78, exit code 1, cmd '/ros2_ws/install/go2_sim/lib/go2_sim/cmd_vel_pub.py --ros-args -r __node:=cmd_vel_pub -r __ns:=/go2 --params-file /tmp/launch_params_gjk3ydvd -r cmd_vel:=/cmd_vel_out'].
go2_ros2    | 2026-05-18 11:49:10.230 | [ERROR] [QuadrupedOdometryNode.py-10]: process has died [pid 80, exit code 1, cmd '/ros2_ws/install/go2_sim/lib/go2_sim/QuadrupedOdometryNode.py --ros-args -r __node:=quadruped_odom --params-file /tmp/launch_params_7p7t7br2 -r imu_plugin/out:=/go2/imu_plugin/out -r robot_velocity:=/go2/robot_velocity -r joint_group_controller/commands:=/go2/joint_group_controller/commands -r foot_contact:=/go2/foot_contact'].
go2_ros2    | 2026-05-18 11:49:10.374 | [INFO] [foxglove_bridge-21]: process has finished cleanly [pid 101]
ollama-1       | [GIN] 2026/05/18 - 04:48:56 | 200 |      43.426µs |       127.0.0.1 | HEAD     "/"
ollama-1       | [GIN] 2026/05/18 - 04:48:56 | 200 |     401.209µs |       127.0.0.1 | GET      "/api/tags"
go2_ros2-1     | [ERROR] [lifecycle_manager-33]: process[lifecycle_manager-33] failed to terminate '5' seconds after receiving 'SIGINT', escalating to 'SIGTERM'
go2_ros2-1     | [ERROR] [planner_server-25]: process[planner_server-25] failed to terminate '5' seconds after receiving 'SIGINT', escalating to 'SIGTERM'
go2_ros2-1     | [INFO] [lifecycle_manager-33]: sending signal 'SIGTERM' to process[lifecycle_manager-33]
go2_ros2-1     | [INFO] [planner_server-25]: sending signal 'SIGTERM' to process[planner_server-25]
go2_ros2-1     | [planner_server-25] [INFO] [1779079737.950075985] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2-1     | [planner_server-25] [INFO] [1779079739.350104475] [planner_server]: Destroying plugin GridBased of type SmacPlannerHybrid
go2_ros2-1     | [planner_server-25] [FATAL] [1779079739.350255600] [planner_server]: Failed to create global planner. Exception: could not create publisher: rcl node's context is invalid, at ./src/rcl/node.c:404
go2_ros2-1     | [planner_server-25] [INFO] [1779079739.350261172] [planner_server]: Cleaning up
go2_ros2-1     | [planner_server-25] [ERROR] [1779079739.350277704] [global_costmap.global_costmap]: Unable to start transition 2 from current state cleaningup: Could not publish transition: publisher's context is invalid, at ./src/rcl/publisher.c:423, at ./src/rcl_lifecycle.c:368
go2_ros2-1     | [planner_server-25] [ERROR] [1779079739.350341348] [planner_server]: Failed to finish transition 1. Current state is now: unconfigured (Could not publish transition: publisher's context is invalid, at ./src/rcl/publisher.c:423, at ./src/rcl_lifecycle.c:368)
go2_ros2-1     | [planner_server-25] Warning: class_loader.ClassLoader: SEVERE WARNING!!! Attempting to unload library while objects created by this loader exist in the heap! You should delete your objects before attempting to unload the library or destroying the ClassLoader. The library will NOT be unloaded.
go2_ros2-1     | [planner_server-25]          at line 127 in ./src/class_loader.cpp
go2_ros2-1     | [planner_server-25] [INFO] [1779079739.390586447] [global_costmap.global_costmap]: Destroying
go2_ros2-1     | [planner_server-25] [WARN] [1779079739.390662724] [rcl_lifecycle]: No transition matching 2 found for current state cleaningup
go2_ros2-1     | [planner_server-25] [INFO] [1779079739.397203380] [planner_server]: Destroying
go2_ros2-1     | [INFO] [planner_server-25]: process has finished cleanly [pid 113]
go2_ros2-1     | [lifecycle_manager-33] [ERROR] [1779079741.351146511] [lifecycle_manager_navigation]: Failed to change state for node: planner_server. Exception: planner_server/get_state service client: async_send_request failed.
go2_ros2-1     | [lifecycle_manager-33] [ERROR] [1779079741.351269124] [lifecycle_manager_navigation]: Failed to bring up all requested nodes. Aborting bringup.
go2_ros2-1     | [lifecycle_manager-33] [INFO] [1779079741.357388000] [rclcpp]: signal_handler(SIGINT/SIGTERM)
go2_ros2-1     | [lifecycle_manager-33] [INFO] [1779079741.357473096] [lifecycle_manager_navigation]: Destroying lifecycle_manager_navigation
go2_ros2-1     | [INFO] [lifecycle_manager-33]: process has finished cleanly [pid 265]
go2_ros2-1 exited with code 0 (restarting)