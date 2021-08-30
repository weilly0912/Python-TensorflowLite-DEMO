# WPI Confidential Proprietary
#--------------------------------------------------------------------------------------
# Copyright (c) 2020 Freescale Semiconductor
# Copyright 2020 WPI
# All Rights Reserved
##--------------------------------------------------------------------------------------
# * Code Ver : 1.0
# * Code Date: 2021/7/30
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
# https://github.com/yeephycho/widerface-to-tfrecord.git
# https://github.com/tensorflow/models.git
# https://github.com/opencv/open_model_zoo.git

import sys
import cv2
import time
import argparse
import numpy as np
from tflite_runtime.interpreter import Interpreter 

# --------------------------------------------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------------------------------------------
# 標註文字
def draw_text_line(img, point, text_line: str):
    fontScale = 0.7
    thickness = 2
    fontFace = cv2.FONT_HERSHEY_SIMPLEX
    text_line = text_line.split("\n")
    baseline_acc = 0
    for i, text in enumerate(text_line):
        if text:
            text_size, baseline = cv2.getTextSize(str(text), fontFace, fontScale, thickness)
            text_loc = (point[0], point[1] + text_size[1])
            cv2.putText(img, str(text), (text_loc[0], text_loc[1] + baseline_acc), fontFace, fontScale,(0, 0, 255), thickness, 8)
            baseline_acc = baseline_acc + int(baseline*3)
    return img

# --------------------------------------------------------------------------------------------------------------
# Define
# --------------------------------------------------------------------------------------------------------------
gender_dict = {0: "woman", 1: "man"}

# --------------------------------------------------------------------------------------------------------------
# 主程式
# --------------------------------------------------------------------------------------------------------------
def main():

    # 解析外部資訊
    APP_NAME = "FacialAgeGender_OpenVINO"
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera", default="0")
    parser.add_argument("--display", default="0")
    parser.add_argument("--save", default="1")
    parser.add_argument("--time", default="0")
    parser.add_argument("--test_img", default="Didy.png")
    parser.add_argument("--offset_y", default="20")
    args = parser.parse_args()

    # 解析解譯器資訊 (人臉位置檢測)
    interpreterFaceExtractor = Interpreter(model_path='mobilenetssd_uint8_face.tflite')
    interpreterFaceExtractor.allocate_tensors() 
    interpreterFaceExtractor_input_details  = interpreterFaceExtractor.get_input_details()
    interpreterFaceExtractor_output_details = interpreterFaceExtractor.get_output_details()
    iFaceExtractor_width    = interpreterFaceExtractor_input_details[0]['shape'][2]
    iFaceExtractor_height   = interpreterFaceExtractor_input_details[0]['shape'][1]
    iFaceExtractor_nChannel = interpreterFaceExtractor_input_details[0]['shape'][3]
    interpreterFaceExtractor.set_tensor(interpreterFaceExtractor_input_details[0]['index'], np.zeros((1,iFaceExtractor_height,iFaceExtractor_width,iFaceExtractor_nChannel)).astype("uint8") ) # 先行進行暖開機
    interpreterFaceExtractor.invoke()

    # 解析解譯器資訊 (年齡)
    interpreterAgeGender = Interpreter(model_path='age-gender-recognition.tflite')
    interpreterAgeGender.allocate_tensors() 
    interpreterAgeGender_input_details  = interpreterAgeGender.get_input_details()
    interpreterAgeGender_output_details = interpreterAgeGender.get_output_details()
    iAgeGender_input_width    = interpreterAgeGender_input_details[0]['shape'][2]
    iAgeGender_input_height   = interpreterAgeGender_input_details[0]['shape'][1]
    iAgeGender_input_nChannel = interpreterAgeGender_input_details[0]['shape'][3]
    interpreterAgeGender.set_tensor(interpreterAgeGender_input_details[0]['index'], np.zeros((1, iAgeGender_input_height, iAgeGender_input_width, iAgeGender_input_nChannel)).astype("uint8"))  # 先行進行暖開機
    interpreterAgeGender.invoke()

    # 是否啟用攝鏡頭
    if args.camera =="True" or args.camera == "1" :
        cap = cv2.VideoCapture("v4l2src device=/dev/video1 ! video/x-raw,format=YUY2,width=1280,height=720,framerate=30/1! videoscale!videoconvert ! appsink")
        if(cap.isOpened()==False) :
            print( "Open Camera Failure !!")
            sys.exit()
        else :
            print( "Open Camera Success !!")

    # 迴圈 / 重複推理   
    while(True):

      # 視訊/影像資料來源
      if args.camera =="True" or args.camera == "1" :
          ret, frame = cap.read()
          frame_resized = cv2.resize(frame, (iFaceExtractor_width, iFaceExtractor_height))

      else : 
          frame         = cv2.imread(args.test_img)
          frame_rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
          frame_resized = cv2.resize(frame_rgb, (iFaceExtractor_width, iFaceExtractor_height))
    
      # 設置來源資料至解譯器、並進行推理 (人臉位置檢測)
      input_data = np.expand_dims(frame_resized, axis=0)
      interpreterFaceExtractor.set_tensor(interpreterFaceExtractor_input_details[0]['index'], input_data) 
      interpreterFaceExtractor.invoke()

      # 取得解譯器的預測結果 (人臉位置檢測)
      detection_boxes   = interpreterFaceExtractor.get_tensor(interpreterFaceExtractor_output_details[0]['index'])
      detection_classes = interpreterFaceExtractor.get_tensor(interpreterFaceExtractor_output_details[1]['index'])
      detection_scores  = interpreterFaceExtractor.get_tensor(interpreterFaceExtractor_output_details[2]['index'])
      num_boxes = interpreterFaceExtractor.get_tensor(interpreterFaceExtractor_output_details[3]['index'])

      # 建立輸出結果 (每個人臉)
      for i in range(1):
        if detection_scores[0, i] > .5: # 當物件預測分數大於 50% 時

          # 物件位置
          x = detection_boxes[0, i, [1, 3]] * frame_rgb.shape[1]
          y = detection_boxes[0, i, [0, 2]] * frame_rgb.shape[0]
          y[1] = y[1] - int(args.offset_y)  #offset

          # 框出偵測到的物件
          rectangle = [x[0], y[0], x[1], y[1]]
          cv2.rectangle(frame, (x[0], y[0]), (x[1], y[1]), (0, 255, 0), 2)

          # --------------------------------------------------------------------------------------------------------
          #  檢測年齡、性別
          # --------------------------------------------------------------------------------------------------------

          #  預防邊界
          roi_x0 = max(0, np.floor(x[0] + 0.5).astype('int32'))
          roi_y0 = max(0, np.floor(y[0] + 0.5).astype('int32'))
          roi_x1 = min(frame.shape[1], np.floor(x[1] + 0.5).astype('int32'))
          roi_y1 = min(frame.shape[0], np.floor(y[1] + 0.5).astype('int32'))

          # 設置來源資料至解譯器 
          if args.camera =="True" or args.camera == "1" : # 輸入端補正
              face_img = frame[ roi_y0 : roi_y1, roi_x0 : roi_x1]  
          else:
              face_img = frame_rgb[ roi_y0 : roi_y1, roi_x0 : roi_x1]  
     
          face_img_resized = cv2.resize(face_img, (iAgeGender_input_height, iAgeGender_input_width))
          face_input_data = np.expand_dims(face_img_resized.astype("uint8"), axis=0)
          interpreterAgeGender.set_tensor(interpreterAgeGender_input_details[0]['index'], face_input_data)

          # 解譯器進行推理
          interpreter_time_start = time.time()
          interpreterAgeGender.invoke()
          interpreter_time_end   = time.time()
          if args.time =="True" or args.time == "1" :
              print( "AgeGender" + " Inference Time = ", (interpreter_time_end - interpreter_time_start)*1000 , " ms" )

          # 取得解譯器的預測結果 
          AgePredict       = interpreterAgeGender.get_tensor(interpreterAgeGender_output_details[1]['index'])
          GenderPredict    = interpreterAgeGender.get_tensor(interpreterAgeGender_output_details[0]['index'])

          # 建立輸出結果 (面網檢測)
          Age       = int(AgePredict[0][0][0][0]*100)
          gender    = gender_dict[np.argmax(GenderPredict)]
          text_info = "Age : " +  str(Age) + " \n"  + "Gender : " + gender 

          #emotion text
          text_x = roi_x0
          text_y = min(np.floor( roi_y0 + 0.5 ).astype('int32'), frame.shape[0])
          frame  = draw_text_line(frame,(text_x, text_y), text_info)

      # 顯示輸出結果
      if args.save == "True" or args.save == "1" :
          cv2.imwrite( APP_NAME + "-" + args.test_img[:len(args.test_img)-4] +'_result.jpg', frame.astype("uint8"))
          print("Save Reuslt Image Success , " + APP_NAME + '_result.jpg')

      if args.display =="True" or args.display == "1" :
          cv2.imshow('frame', frame.astype('uint8'))
          if cv2.waitKey(1) & 0xFF == ord('q'): break

      if args.camera =="False" or args.camera == "0" : sys.exit()

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

