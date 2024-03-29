# -*- coding: utf-8 -*-
"""
Created on Fri Apr  5 15:50:29 2019

@author: johan



This script makes predictions on images of any size.
"""



print("Loading libraries...")
from utils import constants
import os
#os.environ["CUDA_VISIBLE_DEVICES"] = '-1'
from utils import file_utils
import numpy as np
import sys
import tensorflow as tf
from object_detection.utils import visualization_utils


from distutils.version import StrictVersion
from PIL import Image
# This is needed since the notebook is stored in the object_detection folder.
sys.path.append("..")
from object_detection.utils import ops as utils_ops
if StrictVersion(tf.__version__) < StrictVersion('1.9.0'):
  raise ImportError('Please upgrade your TensorFlow installation to v1.9.* or later!')
from object_detection.utils import label_map_util


def predict(project_dir,images_to_predict,output_folder,tile_size,min_confidence_score=0.5,visualize_predictions=True,visualize_groundtruths=False, visualize_scores=False, visualize_names=False, max_iou=0.3):
  """
  Makes predictions on all images in the images_to_predict folder and saves them to the
  output_folder with the prediction bounding boxes drawn onto the images. Additionally
  for each image a json file is saved to the output folder with all the prediction results.
  The images can be of any size and of png, jpg or tif format. If the images
  in the images_to_predict folder have annotation files stored in the same folder,
  these annotation files are also copied to the output folder. This allows the 
  evaluate command to compare the predictions to the groundtruth annotations.
  
  Parameters:
      project_dir (str): path of the project directory, in which the exported
          inference graph is looked for.
      images_to_predict (str): path of the folder containing the images on which
          to run the predictions on.
      output_folder (str): path of the output folder
      tile_size (int): tile_size to use to make predictions on. Should be the same
          as it was trained on.
      prediction_overlap (int): the size of the overlap of the tiles to run the
          prediction algorithm on in pixels

  Returns:
      None
  
  """
    
  MODEL_NAME = project_dir + "/trained_inference_graphs/output_inference_graph_v1.pb"
  # Path to frozen detection graph. This is the actual model that is used for the object detection.
  PATH_TO_FROZEN_GRAPH = MODEL_NAME + '/frozen_inference_graph.pb'
  PATH_TO_LABELS = project_dir + "/model_inputs/label_map.pbtxt"

    
  detection_graph = get_detection_graph(PATH_TO_FROZEN_GRAPH)
  category_index = label_map_util.create_category_index_from_labelmap(PATH_TO_LABELS, use_display_name=True)
  print(category_index)

  with detection_graph.as_default():
   with tf.Session() as sess:
       
       
    tensor_dict = get_tensor_dict()
    image_tensor = tf.get_default_graph().get_tensor_by_name('image_tensor:0') 
    all_images = file_utils.get_all_image_paths_in_folder(images_to_predict)
    
    for image_path in all_images:
        
        image = Image.open(image_path)
        original_width, original_height = image.size

        print("Making Predictions for " + os.path.basename(image_path) + "...")
        
        detections = []
        
        if tile_size != None:
            image = image.resize(tile_size, Image.ANTIALIAS)
        
        #image_np = load_image_into_numpy_array(image)
        image_np = np.asarray(image)         
        image_expand = np.expand_dims(image_np, 0)

        output_dict = sess.run(tensor_dict,feed_dict={image_tensor: image_expand})
        
        output_dict = clean_output_dict(output_dict)
        

        count = 0
        for i,score in enumerate(output_dict['detection_scores']):
            if score >= min_confidence_score:
                count += 1
                top = round(output_dict['detection_boxes'][i][0] * original_height)
                left = round(output_dict['detection_boxes'][i][1] * original_width)
                bottom = round(output_dict['detection_boxes'][i][2] * original_height)
                right = round(output_dict['detection_boxes'][i][3] * original_width)
                detection_class = output_dict['detection_classes'][i]
                detections.append({"bounding_box": [top,left,bottom,right], "score": float(score), "name": category_index[detection_class]["name"]})
                        
        #detections = eval_utils.non_max_suppression(detections,max_iou)
        
        print(str(len(detections)) + " objects detected")
        
        predictions_out_path = os.path.join(output_folder, os.path.basename(image_path)[:-4] + ".xml")
        file_utils.save_annotations_to_xml(detections, image_path, predictions_out_path)

        #copy the ground truth annotations to the output folder if there is any ground truth
        ground_truth = get_ground_truth_annotations(image_path)
        if ground_truth:
            #draw ground truth
            if visualize_groundtruths:
                for detection in ground_truth:
                    [top,left,bottom,right] = detection["bounding_box"]
                    col = "black"
                    visualization_utils.draw_bounding_box_on_image(image,top,left,bottom,right,display_str_list=(),thickness=1, color=col, use_normalized_coordinates=False)          

            ground_truth_out_path = os.path.join(output_folder, os.path.basename(image_path)[:-4] + "_ground_truth.xml")
            file_utils.save_annotations_to_xml(ground_truth, image_path, ground_truth_out_path)
        

        for detection in detections:
            if visualize_predictions:
                col = 'LightCyan'
                [top,left,bottom,right] = detection["bounding_box"]
                score_string = str('{0:.2f}'.format(detection["score"]))
                vis_string_list = []
                if visualize_scores:
                    vis_string_list.append(score_string)
                if visualize_names:
                    vis_string_list.append(detection["name"])                            
                visualization_utils.draw_bounding_box_on_image(image,top,left,bottom,right,display_str_list=vis_string_list,thickness=1, color=col, use_normalized_coordinates=False)          
        
        if visualize_groundtruths or visualize_predictions:
            image_output_path = os.path.join(output_folder, os.path.basename(image_path))
            image.save(image_output_path)



        
def get_ground_truth_annotations(image_path):
    """Reads the ground_thruth information from either the tablet annotations (imagename_annotations.json),
        the LabelMe annotations (imagename.json) or tensorflow xml format annotations (imagename.xml)

    Parameters:
        image_path (str): path to the image of which the annotations should be read
    
    Returns:
        list: a list containing all annotations corresponding to that image.
            Returns the None if no annotation file is present
    """
    ground_truth = file_utils.get_annotations(image_path)
    '''
    for fl in ground_truth:
        fl["name"] = flower_info.clean_string(fl["name"])
        fl["bounding_box"] = flower_info.get_bbox(fl)
    '''
    if len(ground_truth) == 0:                     
        return None
    return ground_truth

        

def get_detection_graph(PATH_TO_FROZEN_GRAPH):
    """
    Reads the frozen detection graph into memory.
    
    Parameters:
        PATH_TO_FROZEN_GRAPH (str): path to the directory containing the frozen
            graph files.
    
    Returns:
        A tensorflow graph instance with which the prediction algorithm can be run.
    """
    detection_graph = tf.Graph()
    with detection_graph.as_default():
      od_graph_def = tf.GraphDef()
      with tf.gfile.GFile(PATH_TO_FROZEN_GRAPH, 'rb') as fid:
        serialized_graph = fid.read()
        od_graph_def.ParseFromString(serialized_graph)
        tf.import_graph_def(od_graph_def, name='')
    return detection_graph

def load_image_into_numpy_array(image):
  """
  Helper function that loads an image into a numpy array.
  
  Parameters:
      image (PIL image): a PIL image
      
  Returns:
      np.array: a numpy array representing the image
  """
  (im_width, im_height) = image.size
  return np.array(image.getdata()).reshape(
      (im_height, im_width, 3)).astype(np.uint8)

def clean_output_dict(output_dict):
    # all outputs are float32 numpy arrays, so convert types as appropriate
    output_dict['num_detections'] = int(output_dict['num_detections'][0])
    output_dict['detection_classes'] = output_dict['detection_classes'][0].astype(np.uint8)
    output_dict['detection_boxes'] = output_dict['detection_boxes'][0]
    output_dict['detection_scores'] = output_dict['detection_scores'][0]
    if 'detection_masks' in output_dict:
        output_dict['detection_masks'] = output_dict['detection_masks'][0]
    return output_dict


def get_tensor_dict():
  """
  Helper function that returns a tensor_dict dictionary that is needed for the 
  prediction algorithm.
  
  Returns:
      dict: The tensor dictionary
  
  """
  
      # Get handles to input and output tensors
  ops = tf.get_default_graph().get_operations()
  all_tensor_names = {output.name for op in ops for output in op.outputs}
  tensor_dict = {}
  for key in ['num_detections', 'detection_boxes', 'detection_scores','detection_classes', 'detection_masks']:
    tensor_name = key + ':0'
    if tensor_name in all_tensor_names:
      tensor_dict[key] = tf.get_default_graph().get_tensor_by_name(tensor_name)    
  return tensor_dict



if __name__ == '__main__':
    
    project_dir = constants.project_folder

    images_to_predict = project_dir + "/images/test"
    
    output_folder = constants.predictions_folder
    
    
    #size of tiles to feed into prediction network
    tile_size = constants.tensorflow_tile_size
    #minimum distance from edge of tile for prediction to be considered
    prediction_overlap = constants.prediction_overlap

    predict(project_dir,images_to_predict,output_folder,tile_size)

    