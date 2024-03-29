# -*- coding: utf-8 -*-
"""
Created on Mon Apr 13 12:52:07 2020

@author: johan
"""

import cv2
import os
import multiprocessing as mp
from itertools import repeat
import signal


'''
def convert(video_path, output_folder,out_size=(640,480)):
    vidcap = cv2.VideoCapture(video_path)
    num_frames = int(vidcap.get(cv2.CAP_PROP_FRAME_COUNT))

    for count in progressbar.progressbar(range(0,num_frames)):
        success,image = vidcap.read()
        out_path = os.path.join(output_folder,"frame%d.png" % count)
        image = cv2.resize(image, (640,480))
        cv2.imwrite(out_path, image)
    
    
def get_frames_every_ms(video_path, output_folder,every_ms=1000/25.0, out_size=(640,480)):
    vidcap = cv2.VideoCapture(video_path)
    num_frames = int(vidcap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = vidcap.get(cv2.CAP_PROP_FPS)
    duration = num_frames/fps
    frames_to_read = int(duration/(every_ms/1000.0))

    

    for count in progressbar.progressbar(range(0,frames_to_read)):
        vidcap.set(cv2.CAP_PROP_POS_MSEC,(count*every_ms))    # added this line 
        success,image = vidcap.read()
        out_path = os.path.join(output_folder,"frame%d.png" % count)
        image = cv2.resize(image, (640,480))
        cv2.imwrite(out_path, image)
        




def make_annotation_frames(video_path, output_folder):
    vidcap = cv2.VideoCapture(video_path)
    num_frames = int(vidcap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = vidcap.get(cv2.CAP_PROP_FPS)
    
    for count in progressbar.progressbar(range(0,num_frames)):
        success,image = vidcap.read()
        out_path = os.path.join(output_folder,"sec_" + str(int(count/fps)) + "_frame_" + str(count % fps) + ".png")
        #image = cv2.resize(image, (640,480))
        cv2.imwrite(out_path, image)
'''


def process_video(group_number, num_processes, video_path, output_folder, out_size=(640,480)):
    
    cap = cv2.VideoCapture(video_path)
    no_of_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
    start_frame = int(no_of_frames / num_processes)* group_number
    end_frame = int(no_of_frames / num_processes)* (group_number+1)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    
    output_path = os.path.join(output_folder,"part_" + str(group_number) + ".mp4")

    out = cv2.VideoWriter(output_path,cv2.VideoWriter_fourcc(*'MP4V'), fps, out_size)

    frame_number = start_frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

    
    try:
        while frame_number < end_frame:
            
            ret, image = cap.read()
            if not ret:
                break
            

            image = cv2.resize(image, out_size)
            out.write(image)

            if (frame_number-start_frame) % 100 == 0:
                print("Thread " + str(group_number) + " progress: " + str(frame_number-start_frame) + " / " + str(end_frame-start_frame))
            frame_number += 1


    except:
        print("Thread " + str(group_number) + ": ERROR!!")
        # Release resources
        cap.release()
        out.release()

    # Release resources
    cap.release() 
    out.release()
    print("Thread " + str(group_number) + ": DONE!")


    


def extract_frames_parallel(video_path,output_folder,out_size=(3840,2160), num_processes=mp.cpu_count()):
    
    original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    pool = mp.Pool(num_processes)
    signal.signal(signal.SIGINT, original_sigint_handler)

    try:
        process_arguments = zip(range(num_processes),repeat(num_processes),repeat(video_path),repeat(output_folder),repeat(out_size))
        pool.starmap(process_video, process_arguments)
    except KeyboardInterrupt:
        print("Caught KeyboardInterrupt, terminating workers")
        pool.terminate()
    else:
        print("Normal termination")
        pool.close()

        

    
    


if __name__ == '__main__':
    input_video = "G:/Johannes/Test/inputs/Test4.MP4"
    output_folder = "G:/Johannes/Test/vid4"
    output_frame_size = (3840,2160)
    num_parts = 8
    
    extract_frames_parallel(input_video,output_folder,output_frame_size,num_parts)
    