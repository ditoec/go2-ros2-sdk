#!/usr/bin/env python3
import numpy as np
from math import sin, cos

class ForwardKinematics:
    def __init__(self, body_dimensions, leg_dimensions):
        """
        Robot parameter initialization.
        :param body_dimensions: Body dimensions [length, width]
        :param leg_dimensions: Leg link dimensions [l1, l2, l3, l4]
        """
        self.body_length = body_dimensions[0]
        self.body_width = body_dimensions[1]

        self.l1 = leg_dimensions[0]  # Body height (from center of mass to leg base)
        self.l2 = leg_dimensions[1]  # Thigh length
        self.l3 = leg_dimensions[2]  # Calf length
        self.l4 = leg_dimensions[3]  # Hoof length

    def homog_transform(self, dx, dy, dz, alpha, beta, gamma):
        """
        Creates a homogeneous 4x4 transformation matrix.
        :param dx, dy, dz: Displacement along x, y, z axes
        :param alpha, beta, gamma: Rotation angles around x, y, z axes (in radians)
        :return: 4x4 transformation matrix
        """
        # Rotation around X axis
        rx = np.array([
            [1, 0, 0, 0],
            [0, cos(alpha), -sin(alpha), 0],
            [0, sin(alpha), cos(alpha), 0],
            [0, 0, 0, 1]
        ])

        # Rotation around Y axis
        ry = np.array([
            [cos(beta), 0, sin(beta), 0],
            [0, 1, 0, 0],
            [-sin(beta), 0, cos(beta), 0],
            [0, 0, 0, 1]
        ])

        # Rotation around Z axis
        rz = np.array([
            [cos(gamma), -sin(gamma), 0, 0],
            [sin(gamma), cos(gamma), 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ])

        # Translation
        trans = np.array([
            [1, 0, 0, dx],
            [0, 1, 0, dy],
            [0, 0, 1, dz],
            [0, 0, 0, 1]
        ])

        # Final transformation matrix: rotations first, then translation
        return trans @ rz @ ry @ rx

    def forward_kinematics_per_leg(self, theta_hip, theta_thigh, theta_calf, leg_index):
        """
        Calculate foot position based on joint angles for one leg.
        :param theta_hip: hip_joint angle (in radians)
        :param theta_thigh: thigh_joint angle (in radians)
        :param theta_calf: calf_joint angle (in radians)
        :param leg_index: Leg index (0: FR, 1: FL, 2: RR, 3: RL)
        :return: Foot position (x, y, z) relative to body
        """
        # Determine base link position for each leg
        if leg_index == 0:  # FR
            base_x = self.body_length / 2
            base_y = self.body_width / 2
        elif leg_index == 1:  # FL
            base_x = self.body_length / 2
            base_y = -self.body_width / 2
        elif leg_index == 2:  # RR
            base_x = -self.body_length / 2
            base_y = self.body_width / 2
        elif leg_index == 3:  # RL
            base_x = -self.body_length / 2
            base_y = -self.body_width / 2
        else:
            raise ValueError("Invalid leg_index. Must be 0 (FR), 1 (FL), 2 (RR), or 3 (RL).")

        # Initial transform: displacement to leg position and body height
        T_base = self.homog_transform(base_x, base_y, -self.l1, 0, 0, 0)

        # hip_joint rotation around Z (abduction/adduction)
        T_hip_abd = self.homog_transform(0, 0, 0, 0, 0, theta_hip)

        # thigh_joint rotation around Y (pitch)
        T_thigh_pitch = self.homog_transform(0, 0, 0, 0, theta_thigh, 0)

        # Displacement along X by thigh length
        T_thigh = self.homog_transform(self.l2, 0, 0, 0, 0, 0)

        # calf_joint rotation around Y (pitch)
        T_calf_pitch = self.homog_transform(0, 0, 0, 0, theta_calf, 0)

        # Displacement along X by calf length
        T_calf = self.homog_transform(self.l3, 0, 0, 0, 0, 0)

        # Displacement along X by hoof length
        T_foot = self.homog_transform(self.l4, 0, 0, 0, 0, 0)

        # Final transformation matrix
        T_total = T_base @ T_hip_abd @ T_thigh_pitch @ T_thigh @ T_calf_pitch @ T_calf @ T_foot

        # Foot position in local coordinate system
        foot_position = T_total @ np.array([0, 0, 0, 1])

        return foot_position[:3]  # Return only x, y, z

    def forward_kinematics_all_legs(self, joint_angles):
        """
        Calculate foot positions for all legs.
        :param joint_angles: List of 12 joint angles [FR_hip, FR_thigh, FR_calf, FL_hip, FL_thigh, FL_calf,
                                                              RR_hip, RR_thigh, RR_calf, RL_hip, RL_thigh, RL_calf]
        :return: List of 4 foot positions [(x_FR, y_FR, z_FR), ..., (x_RL, y_RL, z_RL)]
        """
        if len(joint_angles) != 12:
            raise ValueError("Expected 12 joint angles.")

        foot_positions = []
        for leg in range(4):
            idx = leg * 3
            theta_hip = joint_angles[idx]
            theta_thigh = joint_angles[idx + 1]
            theta_calf = joint_angles[idx + 2]

            foot_pos = self.forward_kinematics_per_leg(theta_hip, theta_thigh, theta_calf, leg)
            foot_positions.append(foot_pos)

        return foot_positions
