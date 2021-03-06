
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
# https://github.com/yeephycho/widerface-to-tfrecord.git
# https://github.com/tensorflow/models.git
# https://google.github.io/mediapipe/solutions/face_mesh.html

# Mediapipe of qaunt tflite need to updat "runtime" version
# May be increase lum of image while using New Web Camera 
# Using "facemesh_weight_flot.tflite" can be accucy result

import sys
import cv2
import time
import argparse
import numpy as np
import tflite_runtime.interpreter as tflite

# --------------------------------------------------------------------------------------------------------------
# Define
# --------------------------------------------------------------------------------------------------------------
CONTIURS_SHAPE_IDX = np.array([10,109,67,103,54,21,162,127,234,93,\
                               132,58,172,136,150,149,176,148,152,\
                               377,378,395,394,365,397,367,416,435,\
                               376,352,345,372,368,300,284,332,297,338])

CONTIURS_LEFT_EYE_IDX  = np.array([226, 247, 29, 27, 28, 56, 133, 154, 145, 144, 163, 25])

CONTIURS_RIGHT_EYE_IDX = np.array([413, 441, 257, 259, 359, 390, 373, 374, 380, 463])

CONTIURS_MOUTH_IDX     = np.array([43, 61, 183, 42, 81, 13, 312, 271, 324, 320, 317, 14, 86, 180, 91])

# --------------------------------------------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------------------------------------------
# ?????????????????? (Non Maximum Suppression)
def nms(boxes, scores, Nt):
    if len(boxes) == 0:
        return [], []
    bboxes = np.array(boxes)
    
    # ?????? n ???????????????????????????
    x1 = bboxes[:, 0]
    y1 = bboxes[:, 1]
    x2 = bboxes[:, 2]
    y2 = bboxes[:, 3]
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    
    # ???????????? (????????????????????????)
    order = np.argsort(scores)
 
    picked_boxes   = []  
    picked_scores  = []  
    while order.size > 0:
        # ??????????????????????????????????????????
        index = order[-1]
        picked_boxes.append(boxes[index])
        picked_scores.append(scores[index])
        
        # ???????????????????????????????????????????????????????????????
        x11 = np.maximum(x1[index], x1[order[:-1]])
        y11 = np.maximum(y1[index], y1[order[:-1]])
        x22 = np.minimum(x2[index], x2[order[:-1]])
        y22 = np.minimum(y2[index], y2[order[:-1]])
        w = np.maximum(0.0, x22 - x11 + 1)
        h = np.maximum(0.0, y22 - y11 + 1)
        intersection = w * h
        
        # ?????????????????????????????????????????????????????????????????????, ????????????????????????????????????
        ious = intersection / (areas[index] + areas[order[:-1]] - intersection)
        left = np.where(ious < Nt)
        order = order[left]

    # ??? numpy
    picked_boxes  = np.array(picked_boxes)
    picked_scores = np.array(picked_scores)

    return picked_boxes, picked_scores

# ?????????????????????????????????????????????????????? list ?????????
def IsFaceContoursAndAppend( point_idx, point_x, point_y, list_index, list_data):
    # ????????????
    if ( point_idx==10  or point_idx==109 or point_idx==67  or point_idx==103 or point_idx==54  or point_idx==21  or point_idx==162 or
         point_idx==127 or point_idx==234 or point_idx==93  or point_idx==132 or point_idx==58  or point_idx==172 or point_idx==136 or
         point_idx==150 or point_idx==149 or point_idx==176 or point_idx==148 or point_idx==152 or point_idx==377 or point_idx==378 or
         point_idx==395 or point_idx==394 or point_idx==365 or point_idx==397 or point_idx==367 or point_idx==416 or point_idx==435 or
         point_idx==376 or point_idx==352 or point_idx==345 or point_idx==372 or point_idx==368 or point_idx==300 or point_idx==284 or
         point_idx==332 or point_idx==297 or point_idx==338)  :
         list_index.append(int(point_idx))
         list_data.append([point_x,point_y])

# ?????????????????????????????????????????????????????? list ?????????
def IsLeftEyeContoursAndAppend( point_idx, point_x, point_y, list_index, list_data):
    # ????????????
    if ( point_idx==226 or point_idx==247 or point_idx==29  or point_idx==27  or point_idx==28 or point_idx==56 or point_idx==133 or 
         point_idx==154 or point_idx==145 or point_idx==144 or point_idx==163 or point_idx==25 )  :
         list_index.append(int(point_idx))
         list_data.append([point_x,point_y])

# ?????????????????????????????????????????????????????? list ?????????
def IsRightEyeContoursAndAppend( point_idx, point_x, point_y, list_index, list_data):
    # ????????????
    if ( point_idx==413 or point_idx==441 or point_idx==257  or point_idx==259  or point_idx==359 or point_idx==390 or point_idx==373 or 
         point_idx==374 or point_idx==380 or point_idx==463)  :
         list_index.append(int(point_idx))
         list_data.append([point_x,point_y])

# ?????????????????????????????????????????????????????? list ?????????
def IsMouthContoursAndAppend( point_idx, point_x, point_y, list_index, list_data):
    # ????????????
    if ( point_idx==43  or point_idx==61  or point_idx==183  or point_idx==42  or point_idx==81 or point_idx==13 or point_idx==312 or 
         point_idx==271 or point_idx==324 or point_idx==320  or point_idx==317 or point_idx==14 or point_idx==86 or point_idx==180 or point_idx==91)  :
         list_index.append(int(point_idx))
         list_data.append([point_x,point_y])

# ?????????????????????????????????
def DrawoutContours( image, contours_correct_indx, contours_list_index, contours_list_data, IsFill):
    # ????????????
    contours = []
    for pt in contours_correct_indx:
        idx = int(np.where(contours_list_index==pt)[0])
        contours.append(contours_list_data[idx])
    contours = np.array([contours]).astype("int32")

    # ????????????
    if (IsFill==0) :
        cv2.drawContours( image, contours, 0, (0,0,0), cv2.FILLED ) 
    else :
        cv2.drawContours( image, contours, 0, (255,255,255), cv2.FILLED ) 

# ????????????
def get_mask_countours_image( mesh_points, image_shape) :
    idx = 0
    contours_shape_idx    = []
    contours_shape_data   = []
    contours_lefteye_idx  = []
    contours_lefteye_data = []
    contours_righteye_idx = []
    contours_righteye_data= []
    contours_mouth_idx = []
    contours_mouth_data= []            
    # ???????????????
    for pt in mesh_points:
        # ???????????????
        x = int(pt[0])
        y = int(pt[1]) 
        IsFaceContoursAndAppend( idx, x, y, contours_shape_idx, contours_shape_data ) # ?????????????????????????????????????????????????????? list ?????????
        IsLeftEyeContoursAndAppend( idx, x, y, contours_lefteye_idx, contours_lefteye_data ) # ?????????????????????????????????????????????????????? list ?????????
        IsRightEyeContoursAndAppend( idx, x, y, contours_righteye_idx, contours_righteye_data ) # ?????????????????????????????????????????????????????? list ?????????
        IsMouthContoursAndAppend( idx, x, y, contours_mouth_idx, contours_mouth_data ) # ?????????????????????????????????????????????????????? list ?????????
        idx = idx + 1 # ??????

    # ????????????????????????????????????
    mask     = np.zeros(image_shape, dtype="uint8")
    DrawoutContours( mask, CONTIURS_SHAPE_IDX    , contours_shape_idx   , contours_shape_data   , 1) # ??????????????????
    #DrawoutContours( mask, CONTIURS_LEFT_EYE_IDX , contours_lefteye_idx , contours_lefteye_data , 0) # ??????????????????
    #DrawoutContours( mask, CONTIURS_RIGHT_EYE_IDX, contours_righteye_idx, contours_righteye_data, 0) # ??????????????????
    #DrawoutContours( mask, CONTIURS_MOUTH_IDX    , contours_mouth_idx   , contours_mouth_data   , 0) # ??????????????????

    # dilation 
    mask = cv2.dilate(mask, np.ones((3,3), np.uint8), iterations = 3)

    return mask

def get_mouth_countours_image( mesh_points, image_shape) :
    idx = 0
    contours_mouth_idx = []
    contours_mouth_data= [] 
    pts_x_max = 0
    pts_y_max = 0
    pts_x_min = 9999
    pts_y_min = 9999    

    # ?????????????????????????????????????????????????????? list ?????????
    for pt in mesh_points:
        x = int(pt[0])
        y = int(pt[1]) 
        IsMouthContoursAndAppend( idx, x, y, contours_mouth_idx, contours_mouth_data )
        idx = idx + 1 # ??????

    # ???????????????????????????
    for x, y in contours_mouth_data:
        if (x>pts_x_max): pts_x_max=x
        if (y>pts_y_max): pts_y_max=y
        if (x<pts_x_min): pts_x_min=x
        if (y<pts_y_min): pts_y_min=y

    # ????????????????????????????????????
    mask     = np.ones(image_shape, dtype="uint8")*255
    DrawoutContours( mask, CONTIURS_MOUTH_IDX    , contours_mouth_idx   , contours_mouth_data   , 0) # ??????????????????

    pts = [ pts_x_min, pts_y_min, pts_x_max, pts_y_max]

    return mask, pts

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
    APP_NAME = "Facemesh_ChangeFace"
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera", default="0")
    parser.add_argument("--display", default="0")
    parser.add_argument("--save", default="1")
    parser.add_argument("--time", default="0")
    parser.add_argument('--delegate' , default="vx", help = 'Please Input nnapi or xnnpack')
    parser.add_argument("--point_size", default="1")
    parser.add_argument("--IoU", default="0.6")
    parser.add_argument("--model", default="facemesh_weight_int8.tflite", help="Using facemesh_weight_flot.tflite can be accucy result")
    parser.add_argument("--test_img", default="licenseface.jpg")
    parser.add_argument("--offset_y", default="15")
    args = parser.parse_args()

    # ????????????????????? (??????????????????)
    interpreterFaceExtractor = InferenceDelegate('mobilenetssd_facedetect_uint8_quant.tflite',args.delegate)
    interpreterFaceExtractor.allocate_tensors() 
    interpreterFaceExtractor_input_details  = interpreterFaceExtractor.get_input_details()
    interpreterFaceExtractor_output_details = interpreterFaceExtractor.get_output_details()
    iFaceExtractor_width    = interpreterFaceExtractor_input_details[0]['shape'][2]
    iFaceExtractor_height   = interpreterFaceExtractor_input_details[0]['shape'][1]
    iFaceExtractor_nChannel = interpreterFaceExtractor_input_details[0]['shape'][3]
    interpreterFaceExtractor.set_tensor(interpreterFaceExtractor_input_details[0]['index'], np.zeros((1,iFaceExtractor_height,iFaceExtractor_width,iFaceExtractor_nChannel)).astype("uint8") ) # ?????????????????????
    interpreterFaceExtractor.invoke()

    # ????????????????????? (????????????)
    interpreterFaceMesh = InferenceDelegate(args.model,args.delegate)
    interpreterFaceMesh.allocate_tensors() 
    interpreterFaceMesh_input_details  = interpreterFaceMesh.get_input_details()
    interpreterFaceMesh_output_details = interpreterFaceMesh.get_output_details()
    iFaceMesh_input_width    = interpreterFaceMesh_input_details[0]['shape'][2]
    iFaceMesh_input_height   = interpreterFaceMesh_input_details[0]['shape'][1]
    iFaceMesh_input_nChannel= interpreterFaceMesh_input_details[0]['shape'][3]
    interpreterFaceMesh.set_tensor(interpreterFaceMesh_input_details[0]['index'], np.zeros((1,iFaceMesh_input_height,iFaceMesh_input_width,iFaceMesh_input_nChannel)).astype("float32"))  # ?????????????????????
    interpreterFaceMesh.invoke()

    # ??????????????????????????? (Lena)
    mask_lena = cv2.imread("Mask_Lena.jpg")
    mask_lena = cv2.cvtColor(mask_lena, cv2.COLOR_BGR2RGB)
    mask_input_data = cv2.resize(mask_lena, (iFaceMesh_input_width, iFaceMesh_input_height)).astype("float32")
    mask_input_data = (mask_input_data)/255
    mask_input_data = (mask_input_data-0.5)/0.5 # [-0.5,0.5] -> [-1, 1]
    mask_input_data = np.expand_dims(mask_input_data, axis=0)
    interpreterFaceMesh.set_tensor(interpreterFaceMesh_input_details[0]['index'], mask_input_data) 
    interpreterFaceMesh.invoke()
    mesh_mask_lena = interpreterFaceMesh.get_tensor(interpreterFaceMesh_output_details[0]['index']).reshape(468, 3)

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
          frame_resized = cv2.resize(frame, (iFaceExtractor_width, iFaceExtractor_height))

      else : 
          frame         = cv2.imread(args.test_img)
          frame_rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
          frame_resized = cv2.resize(frame_rgb, (iFaceExtractor_width, iFaceExtractor_height))
    
      # ???????????????????????????????????????????????? (??????????????????)
      input_data = np.expand_dims(frame_resized, axis=0)
      interpreterFaceExtractor.set_tensor(interpreterFaceExtractor_input_details[0]['index'], input_data) 
      interpreterFaceExtractor.invoke()

      # ?????????????????????????????? (??????????????????)
      detection_boxes   = interpreterFaceExtractor.get_tensor(interpreterFaceExtractor_output_details[0]['index'])
      detection_classes = interpreterFaceExtractor.get_tensor(interpreterFaceExtractor_output_details[1]['index'])
      detection_scores  = interpreterFaceExtractor.get_tensor(interpreterFaceExtractor_output_details[2]['index'])
      num_boxes         = interpreterFaceExtractor.get_tensor(interpreterFaceExtractor_output_details[3]['index'])

      boxs = np.squeeze(detection_boxes)
      scores = np.squeeze(detection_scores)
      boxs_nms, scores_nms = nms(boxs, scores, float(args.IoU))

      # ?????????????????? 
      for i in range( 0, len(scores_nms)-1) : 
        if scores_nms[i] > .5: # ??????????????????????????? 50% ???
        
          # ????????????
          x = boxs_nms[i, [1, 3]] * frame.shape[1]
          y = boxs_nms[i, [0, 2]] * frame.shape[0]
          x[1] = x[1] + int((x[1]-x[0])*0.1)
          y[1] = y[1] + int((y[1]-y[0])*0.05) + int(args.offset_y)

          # ????????????????????????
          cv2.rectangle(frame, ( int(x[0]), int(y[0]) ),  ( int(x[1]), int(y[1]) ), (0, 255, 0), 2) 
          i = len(scores_nms) # ?????????????????????????????????

          # --------------------------------------------------------------------------------------------------------
          #  ????????????  : ??? ????????????????????? ?????????????????????????????????
          # --------------------------------------------------------------------------------------------------------
          #  ????????????
          roi_x0 = max(0, np.floor(x[0] + 0.5).astype('int32'))
          roi_y0 = max(0, np.floor(y[0] + 0.5).astype('int32'))
          roi_x1 = min(frame.shape[1], np.floor(x[1] + 0.5).astype('int32'))
          roi_y1 = min(frame.shape[0], np.floor(y[1] + 0.5).astype('int32'))

          # ?????????????????????????????? ?????????????????????????????? (????????????) 
          if args.camera =="True" or args.camera == "1" : # ???????????????
              face_img = frame[ roi_y0 : roi_y1, roi_x0 : roi_x1] 
          else :
              face_img = frame_rgb[ roi_y0 : roi_y1, roi_x0 : roi_x1] 

          face_img_resize = cv2.resize(face_img, (iFaceMesh_input_width, iFaceMesh_input_height))
          face_input_data = face_img_resize.astype("float32")
          face_input_data = (face_input_data)/255
          face_input_data = (face_input_data-0.5)/0.5 # [-0.5,0.5] -> [-1, 1]
          face_input_data = np.expand_dims(face_input_data, axis=0)
          interpreterFaceMesh.set_tensor(interpreterFaceMesh_input_details[0]['index'], face_input_data) 
          interpreterFaceMesh.invoke()
          mesh_point = interpreterFaceMesh.get_tensor(interpreterFaceMesh_output_details[0]['index']).reshape(468, 3)

          # ????????????????????????????????????????????????
          # https://blog.csdn.net/qq_39507748/article/details/104448700
          featurepoint_sample = np.float32([ mesh_mask_lena[10][:2], mesh_mask_lena[234][:2], mesh_mask_lena[152][:2] ])
          featurepoint_images = np.float32([ mesh_point[10][:2]    , mesh_point[234][:2]    , mesh_point[152][:2] ])
          M = cv2.getAffineTransform(featurepoint_sample, featurepoint_images)
          sample_img = cv2.warpAffine(mask_lena,M,(mask_lena.shape[1],mask_lena.shape[0]),5)
 
          # ???????????? ??????????????????
          sample_img_resize = cv2.resize(sample_img, (iFaceMesh_input_width, iFaceMesh_input_height))
          face_input_data   = sample_img_resize.astype("float32")
          face_input_data   = (face_input_data)/255
          face_input_data   = (face_input_data-0.5)/0.5 # [-0.5,0.5] -> [-1, 1]
          face_input_data   = np.expand_dims(face_input_data, axis=0)
          interpreterFaceMesh.set_tensor(interpreterFaceMesh_input_details[0]['index'], face_input_data) 
          interpreter_time_start = time.time()
          interpreterFaceMesh.invoke()
          interpreter_time_end   = time.time()
          if args.time =="True" or args.time == "1" :
              print( APP_NAME + " Inference Time = ", (interpreter_time_end - interpreter_time_start)*1000 , " ms" )
          mesh_point_sample = interpreterFaceMesh.get_tensor(interpreterFaceMesh_output_details[0]['index']).reshape(468, 3)

          # ???????????????
          mesh_seg        = get_mask_countours_image( mesh_point       , face_img_resize.shape  ) # ???????????????????????????
          mesh_seg_sample = get_mask_countours_image( mesh_point_sample, sample_img_resize.shape) # ?????????????????????????????????
          mask_seg        = np.bitwise_or( mesh_seg, mesh_seg_sample )

          # ???????????? (?????? ????????????)
          """
          mesh_mouth, pts_mouth  = get_mouth_countours_image( mesh_point , face_img_resize.shape  )
          mesh_mouth_dist_x      = int(mesh_point_sample[320][1] - mesh_point[320][1])
          mesh_mouth_dist_y      = int(mesh_point_sample[152][0] - mesh_point[152][0])
          mask_mouth_seg         = mask_seg.copy()
          mask_mouth_seg[ pts_mouth[1] + mesh_mouth_dist_y : pts_mouth[3] + mesh_mouth_dist_y , \
                          pts_mouth[0] + mesh_mouth_dist_x : pts_mouth[2] + mesh_mouth_dist_x ] = \
                          mesh_mouth[ pts_mouth[1]:pts_mouth[3], pts_mouth[0]:pts_mouth[2] ]
          """

          # ????????????
          face_mask = (255-mask_seg)*(face_img_resize*255) + ((sample_img_resize*255)*mask_seg) 
          face_mask = face_mask.astype("uint8")
          face_mask = cv2.resize(face_mask, (face_img.shape[1] , face_img.shape[0]))

          # ?????????????????????????????????
          frame[ roi_y0 : roi_y1, roi_x0 : roi_x1] = cv2.cvtColor(face_mask, cv2.COLOR_BGR2RGB)
              

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


