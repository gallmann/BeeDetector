'''
Choose the video size of the visualizations that are generated by the software.
'''
visualization_video_size=(2048,1152)


'''
Define the number of worker threads. It defines how many videos are processed in 
parallel at most.
Note that the bottleneck of the Software is the GPU. There will be no benefit in
choosing a too high num_worker_threads value. 2-6 worker threads should be sufficient
to keep the GPU fully utilized.
'''
num_worker_threads = 6


'''
A bee will only be tracked over time if it is not further apart than 
(max_tracking_distance_factor*average_hole_height) in two consecutive frames
'''
max_tracking_distance_factor = 1.4

'''
A start of a flight is only counted if the area of the bee detection bounding 
box is smaller than hole_area_factor*average_hole_area.

'''
hole_area_factor = 1.2


'''
A bee is only considered for the evaluation if it is being tracked over at least
min_consecutive_frames_to_track_bee frames.
'''
min_consecutive_frames_to_track_bee = 3


'''
The min_nest_time denotes the minimal time, a bee has to stay inside a hole to qualify 
for residency. (in milliseconds)
'''
min_nest_time = 40000


'''
The min_fly_time denotes the minimal time a bee has to be in flight after leaving
a hole to qualify for residency. (in milliseconds)
'''
min_fly_time = 40000


'''
The following variables define the trained deep learning model paths. Make sure
to only use forward slashes and NO BACKSLASHES in your paths.
'''
bee_model_path = "C:/Users/johan/Desktop/Agroscope/Models/Bee2/trained_inference_graphs/output_inference_graph_v1.pb/frozen_inference_graph.pb"
hole_model_path = "C:/Users/johan/Desktop/Agroscope/Models/Holes2/trained_inference_graphs/output_inference_graph_v1.pb/frozen_inference_graph.pb"
color_model_path = "C:/Users/johan/Desktop/Agroscope/Models/Colors_yolo/trained_model.h5"
number_model_path = "C:/Users/johan/Desktop/Agroscope/Models/Numbers/trained_model.h5"


