from .environment import environment
from .mode_based_actions import Mode
from .numerics import *

import math

class VRRoomscaleAxis:
    def __init__(self):
        self.mode = Mode()              # mode to enable axis
        self.sensitivity = 1.25         # how fast the simulated axis moves/rotates in units/radians per second
        self.centerEpsilon = 0.05       # epsilon around center position to perform center action
        self.holdThreshold = 100000     # a threshold to hold negative or positive when target exceeds this value
        self.current = 0.0              # the simulated current axis value
        self.center = 0.0               # the center position for the center action
        self.centered = True            # whether the axis has been centered
        self.direction = None           # the current movement direction (-1, 1, None)
        self.negativeAction = None      # the action to perform when the axis is decreasing
        self.positiveAction = None      # the action to perform when the axis is increasing
        self.centerAction = None        # the action to perform to center the axis (if available)
        
    def update(self, currentTime, deltaTime, target):
        if self.mode.current == 0:
            return
        
        maxChange = self.sensitivity * deltaTime
        if abs(target - self.current) >= maxChange || abs(target - self.center) > self.holdThreshold:
            if self.centerAction != None and abs(self.center - target) < self.centerEpsilon:
            # reset axis
                if self.direction == 0:
                    self.stopMovement()
                    self.centered = True
                elif self.centered == False:
                    self.stopMovement()
                    self.current = self.center
                    self.centerAction.enter(currentTime, False)
                    self.direction = 0
            
            elif self.current < target or target > self.center + self.holdThreshold:
            # update axis
                self.current = min(target, self.current + maxChange)
                # perform positive movement
                if self.direction == 1:
                    self.positiveAction.update(currentTime)
                else:
                    # stop current movement
                    self.stopMovement()
                    # start positive movement
                    self.centered = False
                    self.direction = 1
                    self.positiveAction.enter(currentTime, False)
                    
            elif self.current > target or target < self.center - self.holdThreshold:
            # update axis
                self.current = max(target, self.current - maxChange)
                # perform negative movement
                if self.direction == -1:
                    self.negativeAction.update(currentTime)
                else:
                    # stop current movement
                    self.stopMovement()
                    # start negative movement
                    self.centered = False
                    self.direction = -1
                    self.negativeAction.enter(currentTime, False)
            else:
                self.stopMovement()
        else:
            self.stopMovement()
    
    def stopMovement(self):
        if self.mode.current == 0:
            return
        
        if self.direction == None:
            return
        
        if self.direction == 0:
            self.centerAction.leave()
        elif self.direction == -1:
            self.negativeAction.leave()
        elif self.direction == 1:
            self.positiveAction.leave()
        
        self.direction = None

#******************************************************************
# Class to handle headset rotaion and movement to discrete actions
# for a duration to reflect that change.
# Use case 1: games with rotation mapped solely to keyboard
# Use case 2: roomscale movement, reflect own movement in game
#******************************************************************
class VRRoomscale:
    def __init__(self):
        self.yaw = VRRoomscaleAxis()
        self.pitch = VRRoomscaleAxis()
        
        self.horizontal = VRRoomscaleAxis()
        self.horizontal.sensitivity = 0.1
        
        self.vertical = VRRoomscaleAxis()
        self.vertical.sensitivity = 0.1
    
        self.headOrigin = Vector()

    def update(self, currentTime, deltaTime):
        if self.yaw.mode.current == 0 and self.pitch.mode.current == 0 and self.horizontal.mode.current == 0 or self.vertical.mode.current == 0:
            return;
            
        yawHead, pitchHead = getYawPitch(environment.openVR.headPose)
        # fix yaw > math.pi
        if self.yaw.current < yawHead - math.pi:
            yawHead = yawHead - 2 * math.pi
        elif self.yaw.current > yawHead + math.pi:
            yawHead = yawHead + 2 * math.pi
        
        self.updateCore(currentTime, deltaTime, self.yaw, yawHead)
        self.updateCore(currentTime, deltaTime, self.pitch, -pitchHead)
        
        headOffset = subtract(environment.openVR.headPose.position, self.headOrigin)
        headOffset = rotateYaw(headOffset, -yawHead)
        
        self.updateCore(currentTime, deltaTime, self.horizontal, headOffset.x)
        self.updateCore(currentTime, deltaTime, self.vertical, -headOffset.z)
    
    def reset(self):
        yawHead, pitchHead = getYawPitch(environment.openVR.headPose)
        self.headOrigin = environment.openVR.headPose.position
        
        self.yaw.current = yawHead
        self.yaw.center = yawHead
        self.pitch.current = pitchHead
        self.horizontal.current = 0
        self.vertical.current = 0
        
        self.yaw.stopMovement()
        self.pitch.stopMovement()
        self.horizontal.stopMovement()
        self.vertical.stopMovement()