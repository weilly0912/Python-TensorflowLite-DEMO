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
# https://github.com/quangnhat185/Plate_detect_and_recognize

import sys
import cv2
import time
import argparse
import numpy as np
import tflite_runtime.interpreter as tflite
from local_utils import reconstruct

# --------------------------------------------------------------------------------------------------------------
# Dedinfe
# --------------------------------------------------------------------------------------------------------------
DIGIT_TEXT_W = 30
DIGIT_TEXT_H = 60
License_dict = { 0: "0",  1: "1",  2: "2",  3: "3",  4: "4",  5: "5",  6: "6",  7:"7",  8:"8",  9:"9",
               10: "A",  11: "B", 12: "C", 13: "D", 14: "E", 15: "F", 16: "G", 17:"H", 18:"I", 19:"J",
               20: "K",  21: "L", 22: "M", 23: "N", 24: "O", 25: "P", 26: "Q", 27:"R", 28:"S", 29:"T",
               30: "U",  31: "V", 32: "W", 33: "X", 34: "Y", 35: "Z"}

# --------------------------------------------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------------------------------------------
def sort_contours(cnts,reverse = False):
    i = 0
    boundingBoxes = [cv2.boundingRect(c) for c in cnts]
    (cnts, boundingBoxes) = zip(*sorted(zip(cnts, boundingBoxes),
                                        key=lambda b: b[1][i], reverse=reverse))
    return cnts

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
    APP_NAME = "PlateDetectAndRecognition"
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera", default="0")
    parser.add_argument("--display", default="0")
    parser.add_argument("--save", default="1")
    parser.add_argument("--time", default="0")
    parser.add_argument('--delegate' , default="vx", help = 'Please Input nnapi or xnnpack')
    parser.add_argument("--test_img", default="germany_car_plate.jpg")
    args = parser.parse_args()

    # ????????????????????? (????????????)
    interpreterPlateDetection = InferenceDelegate('platedetect.tflite',args.delegate)
    interpreterPlateDetection.allocate_tensors() 
    PlateDetection_input_details  = interpreterPlateDetection.get_input_details()
    PlateDetection_output_details = interpreterPlateDetection.get_output_details()
    PlateDetection_width    = PlateDetection_input_details[0]['shape'][2]
    PlateDetection_height   = PlateDetection_input_details[0]['shape'][1]
    PlateDetection_nChannel = PlateDetection_input_details[0]['shape'][3]
    interpreterPlateDetection.set_tensor(PlateDetection_input_details[0]['index'], np.zeros(( 1, PlateDetection_height, PlateDetection_width, PlateDetection_nChannel )).astype("float32") ) # ?????????????????????
    interpreterPlateDetection.invoke()

    # ????????????????????? (????????????)
    interpreterLicenseRecognition = InferenceDelegate('license_recognition.tflite',args.delegate)
    interpreterLicenseRecognition.allocate_tensors() 
    LicenseRecognition_input_details  = interpreterLicenseRecognition.get_input_details()
    LicenseRecognition_output_details = interpreterLicenseRecognition.get_output_details()
    LicenseRecognition_width    = LicenseRecognition_input_details[0]['shape'][2]
    LicenseRecognition_height   = LicenseRecognition_input_details[0]['shape'][1]
    LicenseRecognition_nChannel = LicenseRecognition_input_details[0]['shape'][3]
    interpreterLicenseRecognition.set_tensor(LicenseRecognition_input_details[0]['index'], np.zeros(( 1, LicenseRecognition_height, LicenseRecognition_width, LicenseRecognition_nChannel )).astype("float32") ) # ?????????????????????
    interpreterLicenseRecognition.invoke()

    # ?????????????????????
    if args.camera =="True" or args.camera == "1" :
        cap = cv2.VideoCapture("v4l2src device=/dev/video3 ! video/x-raw,format=YUY2,PlateDetection_width=1280,PlateDetection_height=720,framerate=30/1! videoscale!videoconvert ! appsink")
        if(cap.isOpened()==False) :
            print( "Open Camera Failure !!")
            sys.exit()
        else :
            print( "Open Camera Success !!")

    # ?????? / ????????????       
    while(True):

      # ----------------------------------------------------------------------------------------------------------------
      # ????????????
      # ----------------------------------------------------------------------------------------------------------------
      # ??????/??????????????????
      if args.camera =="True" or args.camera == "1" :
          ret, frame    = cap.read()
          frame_rgb     = frame.astype("float32") /255
          frame_resized = cv2.resize(frame, (PlateDetection_width, PlateDetection_height))

      else : 
          frame         = cv2.imread(args.test_img) 
          frame_rgb     = cv2.cvtColor(frame.astype("float32") /255, cv2.COLOR_BGR2RGB)
          frame_resized = cv2.resize(frame_rgb, (PlateDetection_width, PlateDetection_height))
    
      # ?????????????????????????????? (????????????)
      frame_data = np.expand_dims(frame_resized, axis=0)
      interpreterPlateDetection.set_tensor(PlateDetection_input_details[0]['index'], frame_data) 

      # ????????????????????? (????????????)
      interpreterPlateDetection_time_start = time.time()
      interpreterPlateDetection.invoke()
      interpreterPlateDetection_time_end   = time.time()
      if args.time =="True" or args.time == "1" :
          print( APP_NAME + " Inference Time (Plate Detection) = ", (interpreterPlateDetection_time_end - interpreterPlateDetection_time_start)*1000 , " ms" )

      # ?????????????????????????????? (????????????)
      Features   = interpreterPlateDetection.get_tensor(PlateDetection_output_details[0]['index'])
      Features   = np.squeeze(Features)

      # ?????????????????? (????????????)
      try:
          L, TLp, lp_type, Cor = reconstruct( frame_rgb, frame_resized, Features, lp_threshold=0.5 )
          IsFindLincense = 1
      except:
          print(" No License plate is founded")
          IsFindLincense = 0
      
      # ----------------------------------------------------------------------------------------------------------------
      # ????????????
      # ----------------------------------------------------------------------------------------------------------------
      if (IsFindLincense==1) :

        # ???????????? (???????????????????????????)
        Lincense = (TLp[0]*255).astype("uint8")
        Lincense_gray      = cv2.cvtColor(Lincense, cv2.COLOR_RGB2GRAY)
        Lincense_blur      = cv2.GaussianBlur(Lincense_gray,(7,7),0)
        Lincense_binary    = cv2.threshold(Lincense_blur, 180, 255,cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        Lincense_threshold = cv2.morphologyEx(Lincense_binary, cv2.MORPH_DILATE, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))

        # ??????????????????
        if args.camera =="True" or args.camera == "1" :
            image_result = Lincense.copy()
        else :
            image_result = cv2.cvtColor( Lincense.copy(), cv2.COLOR_BGR2RGB)
        
        # ????????????????????????????????????
        cont, _  = cv2.findContours(Lincense_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        crop_characters = []
        for c in sort_contours(cont):
            (x, y, w, h) = cv2.boundingRect(c)
            ratio = h/w
            if 1<=ratio<=3.5:
                if h/Lincense.shape[0]>=0.5: # ???????????????????????????????????????
                        # ??????
                        cv2.rectangle(image_result, (x, y), (x + w, y + h), (0, 255,0), 2)

                        # ??????????????????
                        curr_num = Lincense_threshold[y:y+h,x:x+w]
                        curr_num = cv2.resize(curr_num, dsize=(DIGIT_TEXT_W, DIGIT_TEXT_H))
                        _, curr_num = cv2.threshold(curr_num, 220, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                        
                        # ?????????????????????????????? (????????????)
                        frame_text = curr_num
                        frame_text_resized = cv2.resize(frame_text, (LicenseRecognition_width, LicenseRecognition_height))
                        frame_text_resized = np.stack((frame_text_resized,)*3, axis=-1)
                        text_data = np.expand_dims(frame_text_resized.astype("float32"), axis=0)
                        interpreterLicenseRecognition.set_tensor(LicenseRecognition_input_details[0]['index'], text_data) 

                        # ????????????????????? (????????????)
                        interpreterLicenseRecognition_time_start = time.time()
                        interpreterLicenseRecognition.invoke()
                        interpreterLicenseRecognition_time_end   = time.time()
                        if args.time =="True" or args.time == "1" :
                            print( APP_NAME + " Inference Time (Text Detection) = ", (interpreterLicenseRecognition_time_end - interpreterLicenseRecognition_time_start)*1000 , " ms" )

                        # ?????????????????????????????? (????????????)
                        text_info = interpreterLicenseRecognition.get_tensor(LicenseRecognition_output_details[0]['index'])
                        text_predict = License_dict[np.argmax(text_info)]
                        crop_characters.append(text_predict)

                        # ????????????
                        cv2.putText( image_result,  str(text_predict), ( x+int(h*0.25), y-int(h*0.1) ), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (0, 0, 255), 1, cv2.LINE_AA)

      else :
          image_result = frame

      # ??????????????????
      if args.save == "True" or args.save == "1" :
          cv2.imwrite( APP_NAME + "-" + args.test_img[:len(args.test_img)-4] +'_result.jpg', image_result.astype("uint8"))
          print("Save Reuslt Image Success , " + APP_NAME + "-" +  args.test_img[:len(args.test_img)-4] + '_result.jpg')

      if args.display =="True" or args.display == "1" :
          cv2.imshow('frame', frame.astype('uint8'))
          if cv2.waitKey(1) & 0xFF == ord('q'): break

      if (args.display =="False" or args.display == "0") and( args.camera =="False" or args.camera == "0" ) : sys.exit()

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
