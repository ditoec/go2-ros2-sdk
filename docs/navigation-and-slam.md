# Navigation and SLAM

## Stack Overview

```
LiDAR (/point_cloud2)
  → pointcloud_to_laserscan_node → /scan
      → slam_toolbox (online_async)  → /map  (OccupancyGrid)
      → Nav2 costmaps (global + local)
          → nav2_planner   → /plan
          → nav2_controller → /cmd_vel
              → twist_mux → /cmd_vel_out → go2_driver_node → robot
```

SLAM and Nav2 run simultaneously by default in `robot.launch.py`. SLAM builds the map in real time while Nav2 uses it for planning.

## SLAM — Creating a Map

1. Launch the full stack: `ros2 launch go2_robot_sdk robot.launch.py`
2. In RViz, find the `SlamToolboxPlugin` panel on the left.
3. Click **"Start At Dock"** — tells slam_toolbox the robot is at the origin.
4. Drive around with the joystick to build the map (white = free, black = occupied, grey = unknown).
5. When done, enter a filename in **"Save Map"** and click it. Then do the same for **"Serialize Map"**.

This creates four files in the working directory:
```
map_1.yaml        — map metadata + path to .pgm
map_1.pgm         — occupancy grid image
map_1.data        — pose graph data
map_1.posegraph   — serialized pose graph
```

## Navigation — Using a Saved Map

1. Launch: `ros2 launch go2_robot_sdk robot.launch.py`
2. In RViz `SlamToolboxPlugin`, enter the map filename (no extension) in **"Deserialize Map"** and click it.
3. Verify the dog's position on the map is correct (orientation matters).
4. In RViz, use **"Nav2 Goal"** tool — click a target point and drag to set the arrival heading.

**Fault symptoms and causes:**

| Symptom | Likely cause |
|---|---|
| Spinning in circles | Map distortion or wrong initial orientation |
| Trying to walk through walls | Map does not match real space |
| No motion / continuous spinning | Overloaded control loop — `controller_frequency` is set to 3.0 Hz intentionally |

## Key Nav2 Parameters (hardware mode)

Tuned conservatively for a quadruped in typical indoor spaces:

```yaml
controller_server:
  controller_frequency: 3.0       # low to avoid overload
  expected_planner_frequency: 1.0

bt_navigator:
  global_frame: map
  robot_base_frame: base_link
  odom_topic: /odom
```

Full params: `go2_robot_sdk/config/nav2_params.yaml` (hardware) and `nav2_params_sim.yaml` (simulation, `use_sim_time: True`).

## SLAM Config

`go2_robot_sdk/config/mapper_params_online_async.yaml` — standard slam_toolbox online async configuration. The same file is used for both hardware and simulation.

## Saving Raw 3D Point Cloud

Set before launching:
```bash
export MAP_SAVE=True
export MAP_NAME="3d_map"   # filename prefix
```

`lidar_to_pointcloud_node` writes `<MAP_NAME>_<timestamp>.ply` to the working directory every 10 s. This is a raw LiDAR dump, not a Nav2 map.
