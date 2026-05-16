#!/usr/bin/env python3
# Author: lnotspotl, abutalipovvv
import numpy as np
import tf_transformations  # Используем tf2 вместо tf
from .StateCommand import State, Command, BehaviorState
from .RestController import RestController
from .TrotGaitController import TrotGaitController
from .CrawlGaitController import CrawlGaitController
from .StandController import StandController
from geometry_msgs.msg import Twist
from quadropted_msgs.msg import RobotModeCommand, RobotVelocity
from quadropted_msgs.srv import RobotBehaviorCommand
class Robot:
    def __init__(self, node, body, legs, imu, robot_id):
        self.body = body
        self.legs = legs
        self.node = node  
        self.robot_id = robot_id  

        self.delta_x = self.body[0] * 0.5
        self.delta_y = self.body[1] * 0.5 + self.legs[1]
        self.x_shift_front = 0.02
        self.x_shift_back = -0.0
        self.default_height = 0.25

        self.trotGaitController = TrotGaitController(
            self.node, self.default_stance,
            stance_time=0.04, swing_time=0.18, time_step=0.02,
            use_imu=imu
        )

        self.crawlGaitController = CrawlGaitController(
            self.default_stance,
            stance_time=0.55, swing_time=0.45, time_step=0.02
        )

        self.standController = StandController(self.node, self.default_stance)  # Передаем node
        self.restController = RestController(self.default_stance)
        self.currentController = self.restController

        self.state = State(self.default_height)
        self.state.foot_locations = self.default_stance
        self.command = Command(self.default_height)

                self.speed_scale = 1.0  # 0.5 = slow, 1.0 = normal, 1.5 = fast

        # Установить режим TROT по умолчанию
        self.command.trot_event = True
        self.command.rest_event = False
        self.command.crawl_event = False
        self.command.stand_event = False

        # Переключиться на TROT
        self.change_controller()



        
        self.node.create_subscription(RobotModeCommand, 'robot_mode', self.mode_callback, 10)
        self.node.create_subscription(RobotVelocity, 'robot_velocity', self.velocity_callback, 10)

        self.behavior_service = self.node.create_service(
            RobotBehaviorCommand,
            'robot_behavior_command',
            self.handle_behavior_command
        )

    def mode_callback(self, msg):
        
        if msg.robot_id == self.robot_id:
            if self.node.verbose:
                self.node.get_logger().info(f"Received mode command: {msg.mode} for robot_id: {msg.robot_id}")
            if msg.mode == "REST":
                self.command.rest_event = True
                self.command.trot_event = False
                self.command.crawl_event = False
                self.command.stand_event = False
            elif msg.mode == "TROT":
                self.command.rest_event = False
                self.command.trot_event = True
                self.command.crawl_event = False
                self.command.stand_event = False
            elif msg.mode == "CRAWL":
                self.command.rest_event = False
                self.command.trot_event = False
                self.command.crawl_event = True
                self.command.stand_event = False
            elif msg.mode == "STAND":
                self.command.rest_event = False
                self.command.trot_event = False
                self.command.crawl_event = False
                self.command.stand_event = True
            
            self.change_controller()

    def velocity_callback(self, msg):

        if msg.robot_id == self.robot_id:
            self.command.velocity = np.array([
                msg.cmd_vel.linear.x * self.speed_scale,
                msg.cmd_vel.linear.y * self.speed_scale,
                msg.cmd_vel.linear.z,
            ])

            self.command.yaw_rate = np.array([
                msg.cmd_vel.angular.x,
                msg.cmd_vel.angular.y,
                msg.cmd_vel.angular.z * self.speed_scale,
            ])
            
            if self.node.verbose:
                self.node.get_logger().info(
                    f"Velocity command updated: linear={self.command.velocity}, angular={self.command.yaw_rate}"
                )

    def handle_behavior_command(self, request, response):
        command = request.command.lower()
        parameter = request.parameter.strip()
        self.node.get_logger().info(f"Behavior command: '{command}' parameter='{parameter}'")

        if command == 'sit':
            self.command.stand_event = True
            self.command.rest_event = False
            self.command.trot_event = False
            self.command.crawl_event = False
            self.change_controller()
            self.state.body_local_position[2] = -0.15
            response.success = True
            response.message = "Sit."

        elif command == 'up':
            self.command.rest_event = True
            self.command.stand_event = False
            self.command.trot_event = False
            self.command.crawl_event = False
            self.change_controller()
            self.state.body_local_position[2] = 0.0
            response.success = True
            response.message = "Stand up."

        elif command == 'walk':
            self.command.rest_event = True
            self.command.trot_event = True
            self.command.stand_event = False
            self.command.crawl_event = False
            self.change_controller()
            self.state.body_local_position[2] = 0.0
            response.success = True
            response.message = "Trot gait active."

        elif command == 'recoverystand':
            self.command.rest_event = True
            self.command.trot_event = True
            self.command.stand_event = False
            self.command.crawl_event = False
            self.change_controller()
            self.state.body_local_position = np.array([0.0, 0.0, 0.0])
            response.success = True
            response.message = "Recovery stand complete."

        elif command == 'euler':
            # parameter: "roll,pitch,yaw" in radians
            try:
                parts = [float(v) for v in parameter.split(',')]
                if len(parts) == 3:
                    self.state.body_local_orientation = np.array(parts)
                    response.success = True
                    response.message = (
                        f"Euler set: roll={parts[0]:.3f} pitch={parts[1]:.3f} yaw={parts[2]:.3f} rad"
                    )
                else:
                    response.success = False
                    response.message = "Euler requires 'roll,pitch,yaw' as parameter."
            except ValueError:
                response.success = False
                response.message = f"Invalid euler parameter: '{parameter}' — expected 'roll,pitch,yaw'"

        elif command == 'bodyheight':
            # parameter: height offset in metres, clamped to ±0.15
            try:
                height = max(-0.15, min(0.15, float(parameter)))
                self.state.body_local_position[2] = height
                response.success = True
                response.message = f"Body height offset set to {height:.3f} m."
            except ValueError:
                response.success = False
                response.message = f"Invalid bodyheight parameter: '{parameter}' — expected float metres"

        elif command == 'speedlevel':
            # parameter: "0"=slow(×0.5)  "1"=normal(×1.0)  "2"=fast(×1.5)
            speed_map = {'0': 0.5, '1': 1.0, '2': 1.5}
            scale = speed_map.get(parameter, None)
            if scale is None:
                response.success = False
                response.message = f"Invalid speedlevel '{parameter}' — use 0, 1, or 2."
            else:
                self.speed_scale = scale
                response.success = True
                response.message = f"Speed level {parameter} (velocity scale ×{scale})."

        elif command == 'stretch':
            # STAND mode with body extended slightly forward and raised
            self.command.stand_event = True
            self.command.rest_event = False
            self.command.trot_event = False
            self.command.crawl_event = False
            self.change_controller()
            self.state.body_local_position = np.array([0.04, 0.0, 0.08])
            response.success = True
            response.message = "Stretch pose applied."

        elif command == 'continuousgait':
            # parameter: "0"=always trot  "1"=rest when velocity is zero (default)
            auto_rest = parameter != '0'
            self.trotGaitController.autoRest = auto_rest
            if not auto_rest:
                self.trotGaitController.trotNeeded = True
            response.success = True
            response.message = f"ContinuousGait: autoRest={'on' if auto_rest else 'off'}."

        else:
            response.success = False
            response.message = f"Unknown command: '{command}'"

        return response

    def change_controller(self):
        if self.command.trot_event and self.command.rest_event:
            # 'walk' REST, to TROT
            self.state.behavior_state = BehaviorState.REST
            self.currentController = self.restController
            self.currentController.pid_controller.reset()
            self.command.rest_event = False
            self.node.get_logger().info("Переключено на REST контроллер")

            #  TROT
            self.state.behavior_state = BehaviorState.TROT
            self.currentController = self.trotGaitController
            self.currentController.pid_controller.reset()
            self.currentController.trotNeeded = True
            self.state.ticks = 0
            self.node.get_logger().info("Переключено на TROT контроллер")
            self.command.trot_event = False

        elif self.command.trot_event:
            if self.state.behavior_state == BehaviorState.REST:
                self.state.behavior_state = BehaviorState.TROT
                self.currentController = self.trotGaitController
                self.currentController.pid_controller.reset()
                self.currentController.trotNeeded = True
                self.state.ticks = 0
            self.command.trot_event = False
            self.node.get_logger().info("Переключено на TROT контроллер")
        
        elif self.command.crawl_event:
            if self.state.behavior_state == BehaviorState.REST:
                self.state.behavior_state = BehaviorState.CRAWL
                self.currentController = self.crawlGaitController
                self.currentController.first_cycle = True
                self.state.ticks = 0
            self.command.crawl_event = False
            self.node.get_logger().info("Переключено на CRAWL контроллер")
        
        elif self.command.stand_event:
            if self.state.behavior_state != BehaviorState.STAND:
                self.state.behavior_state = BehaviorState.STAND
                self.currentController = self.standController
                self.state.body_local_position[2] = 0.005 
                self.node.get_logger().info("Переключено на STAND контроллер")
            self.command.stand_event = False
        
        elif self.command.rest_event:
            self.state.behavior_state = BehaviorState.REST
            self.currentController = self.restController
            self.currentController.pid_controller.reset()
            self.command.rest_event = False
            self.node.get_logger().info("Переключено на REST контроллер")


    def run(self):
        # Возвращаем данные текущего контроллера
        return self.currentController.run(self.state, self.command)

    @property
    def default_stance(self):
        # FR, FL, RR, RL
        return np.array([
            [self.delta_x + self.x_shift_front, self.delta_x + self.x_shift_front, -self.delta_x + self.x_shift_back, -self.delta_x + self.x_shift_back],
            [-self.delta_y, self.delta_y, -self.delta_y, self.delta_y],
            [0, 0, 0, 0]
        ])

