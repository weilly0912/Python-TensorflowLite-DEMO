# WPI Confidential Proprietary
#--------------------------------------------------------------------------------------
# Copyright (c) 2021 Freescale Semiconductor
# Copyright 2021 WPI
# All Rights Reserved
##--------------------------------------------------------------------------------------
# * Code Ver : 2.0
# * Code Date: 2021/12/30
# * Author   : Weilly Li
#--------------------------------------------------------------------------------------
# THIS SOFTWARE IS PROVIDED BY WPI-TW "AS IS" AND ANY EXPRESSED OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL WPI OR ITS CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
# IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
# THE POSSIBILITY OF SUCH DAMAGE.
#--------------------------------------------------------------------------------------
# References:
# https://github.com/google-coral/project-posenet

import sys
import cv2
import time
import math
import argparse
import numpy as np
from enum import Enum
import tflite_runtime.interpreter as tflite

# --------------------------------------------------------------------------------------------------------------
# Define
# --------------------------------------------------------------------------------------------------------------
class Person:
  def __init__(self):
      self.keyPoints = []
      self.score = 0.0

class Position:
  def __init__(self):
    self.x = 0
    self.y = 0

class BodyPart(Enum):
    NOSE = 0,
    LEFT_EYE = 1,
    RIGHT_EYE = 2,
    LEFT_EAR = 3,
    RIGHT_EAR = 4,
    LEFT_SHOULDER = 5,
    RIGHT_SHOULDER = 6,
    LEFT_ELBOW = 7,
    RIGHT_ELBOW = 8,
    LEFT_WRIST = 9,
    RIGHT_WRIST = 10,
    LEFT_HIP = 11,
    RIGHT_HIP = 12,
    LEFT_KNEE = 13,
    RIGHT_KNEE = 14,
    LEFT_ANKLE = 15,
    RIGHT_ANKLE = 16,

class KeyPoint:
  def __init__(self):
    self.bodyPart = BodyPart.NOSE
    self.position = Position()
    self.score = 0.0

# --------------------------------------------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------------------------------------------
def InferenceDelegate( model, delegate ):
    ext_delegate = [ tflite.load_delegate("/usr/lib/libvx_delegate.so") ]
    if (delegate=="vx") :
        interpreter = tflite.Interpreter(model, experimental_delegates=ext_delegate)
    elif(delegate=="xnnpack"):
        interpreter = tflite.Interpreter(model)
    else :
        print("ERROR : Deleget Input Fault")
        return 0
    return interpreter

# --------------------------------------------------------------------------------------------------------------
# ?????????
# --------------------------------------------------------------------------------------------------------------
def main():

    # ??????????????????
    APP_NAME = "PoseEstimation"
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera", default="0")
    parser.add_argument("--display", default="0")
    parser.add_argument("--save", default="1")
    parser.add_argument("--time", default="0")
    parser.add_argument('--delegate' , default="vx", help = 'Please Input nnapi or xnnpack')
    parser.add_argument("--model", default="posenet_mobilenet_v1_075_481_641_quant.tflite")
    parser.add_argument("--test_img", default="AdyAnn.jpg")
    args = parser.parse_args()

    # ?????????????????????
    interpreter = InferenceDelegate(args.model,args.delegate)
    interpreter.allocate_tensors() 
    input_details  = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    width    = input_details[0]['shape'][2]
    height   = input_details[0]['shape'][1]
    nChannel = input_details[0]['shape'][3]
    
    # ?????????????????????
    interpreter.set_tensor(input_details[0]['index'], np.zeros((1,height,width,nChannel)).astype("uint8") )
    interpreter.invoke()

    # ?????????????????????
    if args.camera =="True" or args.camera == "1" :
        cap = cv2.VideoCapture("v4l2src device=/dev/video3 ! video/x-raw,format=YUY2,width=1280,height=720,framerate=30/1! videoscale!videoconvert ! appsink")
        if(cap.isOpened()==False) :
            print( "Open Camera Failure !!")
            sys.exit()
        else :
            print( "Open Camera Success !!")

    # ?????? / ????????????       
    while(True):
      
      # ??????/??????????????????
      if args.camera =="True" or args.camera == "1" :
          ret, frame = cap.read()
          frame_resized = cv2.resize(frame, (width, height))

      else : 
          frame         = cv2.imread(args.test_img)
          frame_rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
          frame_resized = cv2.resize(frame_rgb, (width, height))
    
      # ??????????????????????????????
      input_data = np.expand_dims(frame_resized, axis=0)
      interpreter.set_tensor(input_details[0]['index'], input_data) 

      # ?????????????????????
      interpreter_time_start = time.time()
      interpreter.invoke()
      interpreter_time_end   = time.time()
      if args.time =="True" or args.time == "1" :
          print( APP_NAME + " Inference Time = ", (interpreter_time_end - interpreter_time_start)*1000 , " ms" )

      # ??????????????????????????????
      heat_maps   = interpreter.get_tensor(output_details[0]['index'])
      offset_maps = interpreter.get_tensor(output_details[1]['index'])


      # ??????????????????
      height_ = heat_maps.shape[1]
      width_  = heat_maps.shape[2]
      num_key_points      = heat_maps.shape[3]
      key_point_positions = [[0] * 2 for i in range(num_key_points)]

      # ?????????????????? - ???????????????
      for key_point in range(num_key_points):
        max_val = heat_maps[0][0][0][key_point]
        max_row = 0
        max_col = 0
        for row in range(height_):
          for col in range(width_):
            if heat_maps[0][row][col][key_point] > max_val:
              max_val = heat_maps[0][row][col][key_point]
              max_row = row
              max_col = col
            key_point_positions[key_point] = [max_row, max_col]

      # ?????????????????? - ??????????????? ??? ????????????
      x_coords = [0] * num_key_points
      y_coords = [0] * num_key_points
      confidence_scores = [0] * num_key_points

      for i, position in enumerate(key_point_positions):
        position_y = int(key_point_positions[i][0])
        position_x = int(key_point_positions[i][1])
        y_coords[i] = int(position[0]) 
        x_coords[i] = int(position[1])
        confidence_scores[i] = (float)(heat_maps[0][position_y][position_x][i] /255)
 
      # ?????????????????? - ??????????????????
      person = Person()
      key_point_list = []
      total_score = 0
      for i in range(num_key_points):
        key_point = KeyPoint()
        key_point_list.append(key_point)

      for i, body_part in enumerate(BodyPart):
        key_point_list[i].bodyPart = body_part
        key_point_list[i].position.x = x_coords[i]
        key_point_list[i].position.y = y_coords[i]
        key_point_list[i].score = confidence_scores[i]
        total_score += confidence_scores[i]
      
      # ?????????????????? - ??????????????????
      person.keyPoints = key_point_list
      person.score = total_score / num_key_points
      body_joints = [[BodyPart.LEFT_WRIST, BodyPart.LEFT_ELBOW],
                    [BodyPart.LEFT_ELBOW, BodyPart.LEFT_SHOULDER],
                    [BodyPart.LEFT_SHOULDER, BodyPart.RIGHT_SHOULDER],
                    [BodyPart.RIGHT_SHOULDER, BodyPart.RIGHT_ELBOW],
                    [BodyPart.RIGHT_ELBOW, BodyPart.RIGHT_WRIST],
                    [BodyPart.LEFT_SHOULDER, BodyPart.LEFT_HIP],
                    [BodyPart.LEFT_HIP, BodyPart.RIGHT_HIP],
                    [BodyPart.RIGHT_HIP, BodyPart.RIGHT_SHOULDER],
                    [BodyPart.LEFT_HIP, BodyPart.LEFT_KNEE],
                    [BodyPart.RIGHT_HIP, BodyPart.RIGHT_KNEE],
                    [BodyPart.LEFT_KNEE, BodyPart.LEFT_ANKLE],
                    [BodyPart.RIGHT_KNEE,BodyPart.RIGHT_ANKLE]
                    ]
      

      # ?????????????????? - ?????????????????? (??????????????????)
      for line in body_joints:
        if person.keyPoints[line[0].value[0]].score > 0.4 and person.keyPoints[line[1].value[0]].score > 0.4:
          start_point_x = (int)(person.keyPoints[line[0].value[0]].position.x  * frame.shape[1]/width_)
          start_point_y = (int)(person.keyPoints[line[0].value[0]].position.y  * frame.shape[0]/height_ )
          end_point_x   = (int)(person.keyPoints[line[1].value[0]].position.x  * frame.shape[1]/width_)
          end_point_y   = (int)(person.keyPoints[line[1].value[0]].position.y  * frame.shape[0]/height_ )
          cv2.line(frame, (start_point_x, start_point_y) , (end_point_x, end_point_y), (255, 255, 0), 3)

      # ?????????????????? - ??????????????????
      left_ear_x   = (int)(person.keyPoints[3].position.x  * frame.shape[1]/width_)
      left_ear_y   = (int)(person.keyPoints[3].position.y  * frame.shape[0]/height_)
      right_ear_x  = (int)(person.keyPoints[4].position.x  * frame.shape[1]/width_)
      right_ear_y  = (int)(person.keyPoints[4].position.y  * frame.shape[0]/height_)
      left_shoulder_x   = (int)(person.keyPoints[5].position.x  * frame.shape[1]/width_)
      left_shoulder_y   = (int)(person.keyPoints[5].position.y  * frame.shape[0]/height_)
      right_shoulder_x  = (int)(person.keyPoints[6].position.x  * frame.shape[1]/width_)
      right_shoulder_y  = (int)(person.keyPoints[6].position.y  * frame.shape[0]/height_)
      start_point_x = (int) ((left_ear_x + right_ear_x)/2 )
      start_point_y = left_ear_y
      if(right_ear_y < left_ear_y) : start_point_y = right_ear_y
      end_point_x = (int) ((left_shoulder_x + right_shoulder_x)/2 )
      end_point_y = left_shoulder_y
      if(right_shoulder_y > left_shoulder_y) : end_point_y = right_shoulder_y
      cv2.line(frame, (start_point_x, start_point_y) , (end_point_x, end_point_y), (255, 255, 0), 3)
      
      # ??????????????????
      if args.save == "True" or args.save == "1" :
          cv2.imwrite( APP_NAME + "-" + args.test_img[:len(args.test_img)-4] +'_result.jpg', frame.astype("uint8"))
          print("Save Reuslt Image Success , " + APP_NAME + "-" +  args.test_img[:len(args.test_img)-4] + '_result.jpg')

      if args.display =="True" or args.display == "1" :
          cv2.imshow('frame', frame.astype('uint8'))
          if cv2.waitKey(1) & 0xFF == ord('q'): break

      if (args.display =="False" or args.display == "0") and( args.camera =="False" or args.camera == "0" ) : sys.exit()

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()



