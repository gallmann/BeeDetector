# -*- coding: utf-8 -*-
"""
Created on Mon Apr  1 11:25:16 2019

@author: johan




Running this script, namely its main function convert_annotation_folders, converts one or multiple input folders containing annotated
images into a format that is readable for the Tensorflow library. The input folders
must contain images (jpg, png or tif) and along with each image a json file containing the
annotations. These json files can either be created with the widely used LabelMe Application
or with the AnnotationApp available for Android Tablets.

Output of this string is a folder structure that is used by all subsequent scripts such as
train, predict, evaluate or export-inference-graph scripts and more.
"""




print("Loading libraries...")
from utils import constants
import os
import xml.etree.cElementTree as ET
from PIL import Image
from shutil import move
from shutil import copy
import random
from utils import file_utils
import progressbar
import sys
import urllib.request
import pickle
from yolo3 import convert




def convert_annotation_folders(input_folders, test_splits, validation_splits, project_dir,tensorflow_tile_size = constants.tensorflow_tile_size):
    
    """Converts the contents of a list of input folders into tensorflow readable format ready for training

    Parameters:
        input_folders (list): A list of strings containing all input_folders. 
            The input folders should contain images alongside with annotation
            files. The images can be in png, jpg or tif format. The annotation
            files can either be created with the LabelMe application (imagename.json)
            or with the AnnotationApp (imagename_annotations.json).
        splits (list): A list of floats between 0 and 1 of the same length as 
            input_folders. Each boolean indicates what portion of the images
            inside the corresponding input folder should be used for testing and
            not for training
        project_dir (string): Path of the output directory
        tile_sizes (list): List of ints defining the image tile size to use as Tensorflow input
        split_mode (str): If split_mode is "random", the images are split
            randomly into test and train directory. If split_mode is "deterministic",
            the images will be split in the same way every time this script is 
            executed and therefore making different configurations comparable
        min_flowers (int): Minimum amount of flower needed for including it in the
            training
        overlap (int): overlap in pixels to use during the image tiling process
        
    
    Returns:
        A filled project_dir with all necessary inputs for the Tensorflow model training
    """

    if len(input_folders) > len(test_splits) or len(input_folders) > len(validation_splits):
        print("Error: Make sure that you provide the same number of input folders and split values")
        return

    make_training_dir_folder_structure(project_dir)
    
    download_pretrained_model(project_dir)
    
    labels = {}
    train_images_dir = os.path.join(os.path.join(project_dir, "images"),"train")
    test_images_dir = os.path.join(os.path.join(project_dir, "images"),"test")
    validation_images_dir = os.path.join(os.path.join(project_dir, "images"),"validation")

    for input_folder_index in range(0,len(input_folders)):
        
        input_folder = input_folders[input_folder_index]
                
        image_paths = file_utils.get_all_image_paths_in_folder(input_folder)
        #random.shuffle(image_paths)

        
        
        print("")
        print("Changing image resolution and filtering annotations: (" + input_folder + ")")
        sys.stdout.flush()
        
        
        
        for i in progressbar.progressbar(range(len(image_paths))):
            image_path = image_paths[i]
    
            
            #copying the image along with annotations to the train directory
            if tensorflow_tile_size == None:
                rot_angles = [0]
            else:
                rot_angles = [0]
            
            for rot_angle in rot_angles:
                annotations = file_utils.get_annotations_from_xml(image_path[:-4]+".xml")
                filter_annotations(annotations,labels)
                if rot_angle == 0:
                    dest_image_path = os.path.join(train_images_dir,"inputdir" + str(input_folder_index) + "_" + os.path.basename(image_path))

                else:
                    dest_image_path = os.path.join(train_images_dir,"inputdir" + str(input_folder_index) + "_" +"rot" + str(rot_angle) + "_" + os.path.basename(image_path))

                if tensorflow_tile_size != None:
                    resize_image(image_path,dest_image_path,annotations,tensorflow_tile_size)
                else:
                    image = Image.open(image_path)
                    rotate_annotations(rot_angle,annotations,image)
                    image = image.rotate(rot_angle,expand=True)
                    image.save(dest_image_path)
                    
                    '''
                    for annotation in annotations:
                        [top,left,bottom,right] = annotation["bounding_box"]
                        num_image = image.crop((left, top, right, bottom)) 
                        num_image.save(dest_image_path)
                    '''

                dest_xml_path = dest_image_path[:-4] + ".xml"

                dest_annotations_xml = build_xml_tree(annotations,dest_image_path)
                dest_annotations_xml.write(dest_xml_path)

    
    
    
            
    print("Creating Labelmap file...")
    annotations_dir = os.path.join(project_dir, "model_inputs")
    write_labels_to_labelmapfile(labels,annotations_dir)
    
    print("Splitting train dir into train, test and validation dir...")
    labels_test = {}
    split_train_dir(train_images_dir,test_images_dir, labels, labels_test,"random",input_folders,test_splits)
    labels_validation = {}
    validation_splits = list(validation_splits)
    for i in range(len(validation_splits)):
        validation_splits[i] = validation_splits[i]/(1-min(0.9999,test_splits[i]))
    split_train_dir(train_images_dir,validation_images_dir, labels, labels_validation,"random",input_folders,validation_splits)

            
    print("Training data:")
    print_labels(labels)
    print("Test data:")
    print_labels(labels_test)
    print("Validation data:")
    print_labels(labels_validation)

    print(str(len(labels)) + " classes used for training.")
    print("Done!")

   
def rotate_annotations(rot_angle, annotations, image):
    "rotate counter clock wise"
    width, height = image.size
    for annotation in annotations:
        [top,left,bottom,right] = annotation["bounding_box"]
        if rot_angle == 90:
            annotation["bounding_box"] = [width-right,top,width-left,bottom]
        if rot_angle == 180:
            annotation["bounding_box"] = [height-bottom,width-right,height-top,width-left]
        if rot_angle == 270:
            annotation["bounding_box"] = [left,height-bottom,right,height-top]


def resize_image(image_path,dest_image_path,annotations,size=None):
    
    image = Image.open(image_path)
    width, height = image.size
    if not size: 
        (dest_width,dest_height) = (width, height)
    else:
        (dest_width,dest_height) = size

    
    x_resize_ratio = dest_width/width
    y_resize_ratio = dest_height/height
    
    image = image.resize(size, Image.ANTIALIAS)
    
    for annotation in annotations:
        [top,left,bottom,right] = annotation["bounding_box"]
        top = int(top*y_resize_ratio)
        bottom = int(bottom*y_resize_ratio)
        left = int(left*x_resize_ratio)
        right = int(right*x_resize_ratio)
        annotation["bounding_box"] = [top,left,bottom,right]
    image.save(dest_image_path)

    

    

def filter_annotations(annotations,labels):
    for annotation in annotations:
        #Remove all spaces
        #filtered_name = annotation["name"].rstrip()
        #Remove all spaces and numbers from annotation name
        #filtered_name = ''.join(x for x in annotation["name"] if x.isdigit()).rstrip()
        filtered_name = ''.join(x for x in annotation["name"] if not x.isdigit()).rstrip()

        annotation["name"] = filtered_name        
        
        add_label_to_labelcount(filtered_name, labels)
        
    


def split_train_dir(src_dir,dst_dir,labels, labels_dst,split_mode,input_folders,splits, full_size_splitted_dir = None):
    """Splits all annotated images into training and testing directory

    Parameters:
        src_dir (str): the directory path containing all images and xml annotation files 
        dst_dir (str): path to the test directory where part of the images (and 
                 annotations) will be copied to
        labels (dict): a dict inside of which the flowers are counted
        labels_dst (dict): a dict inside of which the flowers are counted that
            moved to the dst directory
        split_mode (str): If split_mode is "random", the images are split
            randomly into test and train directory. If split_mode is "deterministic",
            the images will be split in the same way every time this script is 
            executed and therefore making different configurations comparable
        input_folders (list): A list of strings containing all input_folders. 
        splits (list): A list of floats between 0 and 1 of the same length as 
            input_folders. Each boolean indicates what portion of the images
            inside the corresponding input folder should be used for testing or validating and
            not for training
        test_dir_full_size (str): path of folder to which all full size original
            images that are moved to the test directory should be copied to.
            (this folder can be used for evaluation after training) (default is None)
    
    Returns:
        None
    """

    images = file_utils.get_all_image_paths_in_folder(src_dir)

    for input_folder_index in range(0,len(input_folders)):
        portion_to_move_to_test_dir = float(splits[input_folder_index])
        images_in_current_folder = []
        image_names_in_current_folder = []
        

        #get all image_paths in current folder
        for image_path in images:
            if "inputdir" + str(input_folder_index) in image_path:
                images_in_current_folder.append(image_path)
                image_name = os.path.basename(image_path).split("_subtile",1)[0] 
                if not image_name in image_names_in_current_folder:
                    image_names_in_current_folder.append(image_name)
            
        if split_mode == "random":
        
            #shuffle the images randomly
            random.shuffle(images_in_current_folder)
            #and move the first few images to the test folder
            for i in range(0,int(len(images_in_current_folder)*portion_to_move_to_test_dir)):
                move_image_and_annotations_to_folder(images_in_current_folder[i],dst_dir,labels,labels_dst)
    
        elif split_mode == "deterministic":
                    
            #move every 1/portion_to_move_to_test_dir-th image to the dst_dir
            split_counter = 0.5
            #loop through all image_names (corresponding to untiled original images)
            for image_name in image_names_in_current_folder:
                split_counter = split_counter + portion_to_move_to_test_dir
                #if the split_counter is greater than one, all image_tiles corresponding to that original image should be
                #moved to the test directory
                if split_counter >= 1:
                    if full_size_splitted_dir:
                        original_image_name = os.path.join(input_folders[input_folder_index], image_name)
                        copy(original_image_name,os.path.join(full_size_splitted_dir,"inputdir" + str(input_folder_index) + "_" +image_name))
                        copy(original_image_name[:-4] + "_annotations.json",os.path.join(full_size_splitted_dir,"inputdir" + str(input_folder_index) + "_" +image_name[:-4] + "_annotations.json"))

                    for image_tile in images_in_current_folder:
                        if image_name in os.path.basename(image_tile):
                            move_image_and_annotations_to_folder(image_tile,dst_dir,labels,labels_dst)
                    split_counter = split_counter -1
                    
            

            

def move_image_and_annotations_to_folder(image_path,dest_folder, labels, labels_test):
    """Moves and image alonside with its annotation file to another folder and updates the flower counts

    Parameters:
        image_path (str): path to the image
        dest_folder (str): path to the destination folder
        labels (dict): a dict inside of which the flowers are counted
        labels_test (dict): a dict inside of which the flowers are counted that
            moved to the test directory
    
    Returns:
        None
    """

    image_name = os.path.basename(image_path)
    xml_name = os.path.basename(image_path)[:-4] + ".xml"

    #update the labels count to represent the counts of the training data
    xmlTree = ET.parse(image_path[:-4] + ".xml")
    root = xmlTree.getroot()

    for child in root:
        if(child.tag == "object"):
            for att in child:
                if(att.tag == "name"):
                    flower_name = att.text
                    labels[flower_name] = labels[flower_name]-1
                    add_label_to_labelcount(flower_name,labels_test)
    move(image_path,os.path.join(dest_folder,image_name))
    move(image_path[:-4] + ".xml",os.path.join(dest_folder,xml_name))


def write_labels_to_labelmapfile(labels, output_path):
    """Given a list of labels, prints them to a labelmap file needed by tensorflow

    Parameters:
        labels (dict): a dict inside of which the flowers are counted
        output_path (str): a directory path where the labelmap.pbtxt file should be saved to
    
    Returns:
        None
    """

        
    output_pkl = os.path.join(output_path,"label_map.pkl")
    with open(output_pkl, 'wb') as f:
        pickle.dump(sorted(labels), f, pickle.HIGHEST_PROTOCOL)

    output_name = os.path.join(output_path, "label_map.pbtxt")
    end = '\n'
    s = ' '
    out = ''

    for ID, name in enumerate(sorted(labels)):
        out += 'item' + s + '{' + end
        out += s*2 + 'id:' + ' ' + (str(ID+1)) + end
        out += s*2 + 'name:' + ' ' + '\'' + name + '\'' + end
        out += '}' + end*3
        
    
    with open(output_name, 'w') as f:
        f.write(out)
            
            
def build_xml_tree(annotations, image_path):
    """Given a list of flowers, this function builds an xml tree from it. The XML tree is needed to create the tensorflow .record files

    Parameters:
        flowers (list): a list of flower dicts
        image_path (str): the path of the corresponding image
        labels (dict): a dict inside of which the flowers are counted

    Returns:
        None
    """

    root = ET.Element("annotation")
    
    image = Image.open(image_path)
    ET.SubElement(root, "filename").text = os.path.basename(image_path)
    
    width, height = image.size
    size = ET.SubElement(root, "size")
    ET.SubElement(size, "width").text = str(width)
    ET.SubElement(size, "height").text = str(height)
    
    for annotation in annotations:
        flower_name = annotation["name"]
        
        annotation_object = ET.SubElement(root, "object")
        ET.SubElement(annotation_object, "name").text = flower_name
        ET.SubElement(annotation_object, "pose").text = "Unspecified"
        ET.SubElement(annotation_object, "truncated").text = str(0)
        ET.SubElement(annotation_object, "difficult").text = str(0)            
        bndbox = ET.SubElement(annotation_object, "bndbox")

        [top,left,bottom,right] = annotation["bounding_box"]
        ET.SubElement(bndbox, "xmin").text = str(left)
        ET.SubElement(bndbox, "ymin").text = str(top)
        ET.SubElement(bndbox, "xmax").text = str(right)
        ET.SubElement(bndbox, "ymax").text = str(bottom)
            
            
        #visualization_utils.draw_bounding_box_on_image(image,y - bounding_box_size,x - bounding_box_size,y + bounding_box_size,x + bounding_box_size,display_str_list=(),thickness=1, use_normalized_coordinates=False)

    #image.save(image_path)
    tree = ET.ElementTree(root)
    return tree

#small helper function to keep track of how many flowers of each species have been annotated 
def add_label_to_labelcount(flower_name, label_count):
    """Small helper function to to add a flower to a label_count dict
    
    Parameters:
        flower_name (str): name of the flower to add to the dict
        label_count (dict): a dict inside of which the flowers are counted

    Returns:
        None
    """

    if(label_count.get(flower_name) == None):
        label_count[flower_name] = 1
    else:
        label_count[flower_name] = label_count[flower_name] + 1


def make_training_dir_folder_structure(root_folder):
    """Creates the whole folder structure of the output. All subsequent scripts such as train.py, predict.py, export_inference_graph.py or eval.py rely on this folder structure
    
    Parameters:
        root_folder (str): path to a folder inside of which the project folder structure is created

    Returns:
        None
    """

    images_folder = os.path.join(root_folder, "images")
    os.makedirs(images_folder,exist_ok=True)
    file_utils.delete_folder_contents(images_folder)
    os.makedirs(os.path.join(images_folder,"test"),exist_ok=True)
    os.makedirs(os.path.join(images_folder,"train"),exist_ok=True)
    #os.makedirs(os.path.join(images_folder,"test_full_size"),exist_ok=True)
    os.makedirs(os.path.join(images_folder,"validation"),exist_ok=True)
    #os.makedirs(os.path.join(images_folder,"validation_full_size"),exist_ok=True)
    prediction_folder = os.path.join(root_folder,"predictions")
    os.makedirs(prediction_folder,exist_ok=True)
    os.makedirs(os.path.join(prediction_folder,"evaluations"),exist_ok=True)
    os.makedirs(os.path.join(root_folder,"model_inputs"),exist_ok=True)
    os.makedirs(os.path.join(root_folder,"predictions"),exist_ok=True)
    os.makedirs(os.path.join(root_folder,"pre-trained-model"),exist_ok=True)
    trained_inference_graphs_folder = os.path.join(root_folder,"trained_inference_graphs")
    os.makedirs(trained_inference_graphs_folder,exist_ok=True)
    os.makedirs(os.path.join(trained_inference_graphs_folder,"output_inference_graph_v1.pb"),exist_ok=True)
    training_folder = os.path.join(root_folder,"training")
    os.makedirs(training_folder,exist_ok=True)
    #os.makedirs(os.path.join(root_folder,"eval"),exist_ok=True)
    validation_folder = os.path.join(root_folder,"validation")
    os.makedirs(validation_folder,exist_ok=True)
    os.makedirs(os.path.join(validation_folder,"evaluation"),exist_ok=True)



def print_labels(labels):
    """Prints the label_count dict to the console in readable format
    
    Parameters:
        labels (dict): a dict inside of which the flowers are counted
        flowers_to_use (list): list of strings of the flower names that should
            be used for training
    Returns:
        None
    """

    for key in sorted(labels):
        print("    " + key + ": " + str(labels[key]))
    

pbar = None

def download_pretrained_model(project_folder):    
    
    pretrained_model_folder = os.path.join(project_folder,"pre-trained-model")
    
    destination_file = os.path.join(pretrained_model_folder,"yolov3.weights")
    output_path = os.path.join(pretrained_model_folder,"yolov3.h5")

    if not os.path.isfile(output_path):
       
        def show_progress(block_num, block_size, total_size):
            global pbar
            if pbar is None:
                pbar = progressbar.ProgressBar(maxval=total_size)
        
            downloaded = block_num * block_size
            if downloaded < total_size:
                pbar.update(downloaded)
            else:
                pbar.finish()
                pbar = None

        
        print("Downloading pretrained model...")
        # Download the file from `url` and save it locally under `file_name`:
        destination_file_cfg = os.path.join(pretrained_model_folder,"yolov3.cfg")
        urllib.request.urlretrieve("https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3.cfg", destination_file_cfg, show_progress)
        
        
        urllib.request.urlretrieve("https://pjreddie.com/media/files/yolov3.weights", destination_file, show_progress)

        convert._main(destination_file_cfg,destination_file,output_path)
        
        
        
        
if __name__== "__main__":
    
    
    input_folders = ["C:/Users/johan/Desktop/Data/video4/colors5",
                     "C:/Users/johan/Desktop/Data/video4/colors2",
                     "C:/Users/johan/Desktop/Data/video4/colors1",
                     "C:/Users/johan/Desktop/Data/video4/colors6",
                     "C:/Users/johan/Desktop/Data/video5/colors",
                     "C:/Users/johan/Desktop/Data/video2/colors",
                     "C:/Users/johan/Desktop/Data/video6/colors",
                     "C:/Users/johan/Desktop/Data/video7/colors",
                     "C:/Users/johan/Desktop/Data/video8/colors"
                     ]
    
    test_splits = [0.0,
                   0.0,
                   0.0,
                   0.0,
                   0.0,
                   0.0,
                   0.0,
                   0.0,
                   0.0]
    
    validation_splits = [0.1,
                         0.1,
                         0.1,
                         0.1,
                         0.1,
                         0.1,
                         0.1,
                         0.1,
                         0.1]

    #All outputs will be saved into this folder
    project_folder = "C:/Users/johan/Desktop/color_training"
        
    
        
    convert_annotation_folders(input_folders, test_splits,validation_splits, project_folder, tensorflow_tile_size=None)

