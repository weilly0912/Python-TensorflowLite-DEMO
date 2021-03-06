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
# https://github.com/tensorflow/models.git
# https://github.com/fllay/totoro.git


import sys
import cv2
import time
import argparse
import numpy as np
import tflite_runtime.interpreter as tflite

# --------------------------------------------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------------------------------------------
def normalization(data):
    _range = np.max(data) - np.min(data)
    return (data - np.min(data)) / _range

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
    APP_NAME = "BodyPix"
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera", default="0")
    parser.add_argument("--display", default="0")
    parser.add_argument("--save", default="1")
    parser.add_argument("--time", default="0")
    parser.add_argument('--delegate' , default="vx", help = 'Please Input nnapi or xnnpack')
    parser.add_argument('--model' , default="bodypix_concrete.tflite", help='File path of .tflite file.')
    parser.add_argument("--test_img", default="bodypix_test.png")
    parser.add_argument("--backgorund", default="London.jpg")
    parser.add_argument("--seg_threshold", default="245", help ="may should setting value is 200")
    args = parser.parse_args()

    # ??????????????????
    backgorund_img = cv2.imread(args.backgorund)

    # ?????????????????????
    interpreter = InferenceDelegate(args.model,args.delegate)
    interpreter.allocate_tensors() 
    input_details  = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    width    = input_details[0]['shape'][2]
    height   = input_details[0]['shape'][1]
    nChannel = input_details[0]['shape'][3]

    # ?????????????????????
    interpreter.set_tensor(input_details[0]['index'], np.zeros((1,height,width,nChannel)).astype("float32") )
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
          ret, frame    = cap.read()
          frame_resized = cv2.resize(frame, (width, height))

      else : 
          frame         = cv2.imread(args.test_img)
          frame_rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
          frame_resized = cv2.resize(frame_rgb, (width, height))
    
      # ??????????????????????????????
      input_data = np.expand_dims(frame_resized.astype("float32"), axis=0)
      input_data = (input_data-128) / 255
      interpreter.set_tensor(input_details[0]['index'], input_data) 

      # ?????????????????????
      interpreter_time_start = time.time()
      interpreter.invoke()
      interpreter_time_end   = time.time()
      if args.time =="True" or args.time == "1" :
          print( APP_NAME + " Inference Time = ", (interpreter_time_end - interpreter_time_start)*1000 , " ms" )

      # ??????????????????????????????
      seg = interpreter.get_tensor(output_details[6]['index'])
      seg = seg.reshape(output_details[6]['shape'][1], output_details[6]['shape'][2] )

      # ?????????????????? - ?????????????????????
      th = int(args.seg_threshold)
      seg = normalization(seg)*255
      seg = cv2.resize(seg, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_CUBIC )
      ret, segmentation = cv2.threshold(seg, th, 255, cv2.THRESH_BINARY)
      segmentation = cv2.cvtColor(segmentation, cv2.COLOR_GRAY2RGB)

      # ?????????????????? - ????????????
      body = (segmentation/255)*frame

      # ?????????????????? - ????????????
      backgorund_img  = cv2.resize(backgorund_img, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_AREA)
      Background      = (1 - (segmentation/255))*backgorund_img

      # ?????????????????? - ????????????
      result = body + Background

      # ????????????
      """
      result = result.astype("uint8")
      tmp    = result.copy()
      mask   = np.ones(result.shape, result.dtype)
      center = ( result.shape[0] // 2, result.shape[1] // 2 )
      dst    = cv2.seamlessClone( tmp, tmp, mask, center, 1)
      """

      # ??????????????????
      if args.save == "True" or args.save == "1" :
          cv2.imwrite( APP_NAME + "-" + args.test_img[:len(args.test_img)-4] + "_" + str(args.backgorund[:-4]) +'_result.jpg', result.astype("uint8"))
          print("Save Reuslt Image Success , " + APP_NAME + "_" + str(args.backgorund[:-4]) + '_result.jpg')

      if args.display =="True" or args.display == "1" :
          cv2.imshow('frame', result.astype('uint8'))
          if cv2.waitKey(1) & 0xFF == ord('q'): break

      if (args.display =="False" or args.display == "0") and( args.camera =="False" or args.camera == "0" ) : sys.exit()

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
