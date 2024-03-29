import csv
import math
import os
# Bee Counting
# Author: Flurin Schwerzmann


'''
Parameters:
    csv_file_name: input file with all unfiltered events
    min_nest_time: time a bee has to stay inside a hole to qualify for residency in milliseconds
    min_fly_time: time a bee has to be in flight to qualify for residency in milliseconds
'''

def seconds_to_string(seconds):
    if seconds < 10:
        return "0" + str(seconds)
    return str(seconds)

def extract_agroscope_metrics(csv_file_name, output_folder, min_nest_time=40000, min_fly_time=40000):

    # VARIABLES
    
    data = []  # TIME, BEE, ACTION, HOLE, RESIDENTIAL_MOVEMENT
    multi_nests = []  # nests used by more than one bee
    multi_residents = []  # bees with more than one nest
    errors = []  # list of erroneous movements
    residential_movements = []  # list of movements qualifying for residency
    address_book = []  # list of nests used by no more than one bee
    boozer_book = []  # list with the number of holes a bee went into before finding it's nest
    flight_book = []  # list with duration of collecting flights
        
    debug_error_correction = False
    debug_find_residents = False
    debug_multi_residents = False
    debug_show_error_list = False
    
    
    # convert a timestamp to milliseconds
    def timestamp_to_millis(timestamp):
        hms = timestamp.split(':')
        return float(hms[0]) * 3.6E6 + float(hms[1]) * 60E3 + float(hms[2]) * 1000
    
    def millis_to_timestamp(millis):
        one_hour_in_millis = 1000*60*60
        hours = math.floor(millis / one_hour_in_millis)
        minutes = math.floor((millis % one_hour_in_millis) / 60000)
        seconds = math.floor((millis % 60000) / 1000 )
        if hours < 10:
            hours = "0" + str(hours)
        if minutes < 10:
            minutes = "0" + str(minutes)
        if seconds < 10:
            seconds = "0" + str(seconds)
    
        return str(hours) + ":" + str(minutes) + ":" + str(seconds)

    
    # convert milliseconds to minutes and seconds
    def millis_to_min_sec(millis):
        minutes = math.floor(millis / 60000)
        if minutes < 10:
            minutes = "0" + str(minutes)
    
        seconds = round((millis % 60000) / 1000)
        if seconds < 10:
            seconds = "0" + str(seconds)
    
        return [minutes, seconds]

    
    # FUNCTIONS
    
    # correction principle: insert a fitting movement
    # used for hole-ordered search as well as bee-ordered search
    def correct_missing_movement(index, search_type):

        if debug_error_correction:
            print("--- Error Correction: " + search_type + " ---")
            print("Old:")
            print(data[index - 1])
            print(data[index])
            print(data[index + 1])
            print(data[index + 2])
    
        # enter: insert leave
        if "Enter" in data[index][2]:
            # the timestamp of the inserted leave is exactly 1 millisecond after
            new_movement_timestamp = millis_to_timestamp(timestamp_to_millis(data[index][0]) + 0.001)
            data.insert(index+1,[new_movement_timestamp, data[index][1], 'Missing Leave', data[index][3]])

        # leave: insert enter
        elif 'Leave' in data[index][2]:
            # the timestamp of the inserted enter is exactly 1 millisecond before
            new_movement_timestamp = millis_to_timestamp(timestamp_to_millis(data[index+1][0]) - 0.001)
            data.insert(index+1,[new_movement_timestamp, data[index][1], 'Missing Enter', data[index+1][3]])
    
        if debug_error_correction:
            print("New:")
            print(data[index - 1])
            print(data[index])
            print(data[index + 1])
            print(data[index + 2])
            print(data[index + 3])
    
        
    
    # take measurements of a valid movement qualified as residence
    # drunkenness: number of holes a bee flies to before finding it's nest
    # collection time: time between leaving home for a collection flight and finding home again afterwards
    def take_measurements(index, home, bee):
        time_leaving_home = data[index + 1][0]
        drunkenness = 0
        correction = 0
        # make sure to keep track on the same bee
        while len(data) > index + (2 * drunkenness) + 2 and data[index + (2 * drunkenness) + 2][1] == bee:
            # check if bee has found it's home (with valid enter movement)
            if data[index + (2 * drunkenness) + 2][3] == home and data[index + (2 * drunkenness) + 2][2] == 'Enter':
                #print(str(bee) + " flew to " + str(drunkenness) + " holes before finding it's nest " + str(home))
                boozer_book.append([time_leaving_home, bee, drunkenness - correction])
                
                time_back_home = data[index + (2 * drunkenness) + 2][0]
                collection_time = timestamp_to_millis(time_back_home) - timestamp_to_millis(time_leaving_home)
                flight_book.append([time_leaving_home, bee, millis_to_min_sec(collection_time)])
    
                return
            
            #break if bee stays inside a hole other than home for longer than min_nest_time
            if drunkenness > 0 and timestamp_to_millis(data[index + (2 * drunkenness) + 1][0]) - timestamp_to_millis(data[index + (2 * drunkenness)][0]) > min_nest_time:
                return
    
            # make sure to correct for inserted missing movements
            if "Missing" in data[index + (2 * drunkenness) + 2][2]:
                correction += 1
            elif len(data) > index + (2 * drunkenness) + 3 and "Missing" in data[index + (2 * drunkenness) + 3][2] and data[index + (2 * drunkenness) + 3][1] == bee:
                correction += 1
    
            drunkenness += 1
    
    
    # check if movement qualifies for confirmation of residence
    # if residence is detected, measurements are taken and the movement is registered as residential movement
    def check_resident(index):
        # residency check always starts with enter
        if data[index][2] == 'Enter':
            nest_time = timestamp_to_millis(data[index + 1][0]) - timestamp_to_millis(data[index][0])
            fly_time = timestamp_to_millis(data[index + 2][0]) - timestamp_to_millis(data[index + 1][0])
            # times must be great enough to qualify as a resident
            if nest_time > min_nest_time and fly_time > min_fly_time:
                # avoid corrected movements
                if data[index + 1][2] == 'Leave' and data[index + 2][2] == 'Enter':
                    if debug_find_residents:
                        print("Found resident: " + str(data[index]))
                    residential_movements.append([data[index][3], data[index][1]])
                    data[index][4] = data[index][4] + "residential movement " + str(len(residential_movements)) + ", "
                    data[index+1][4] = data[index+1][4] + "residential movement " + str(len(residential_movements)) + ", "
                    data[index+2][4] = data[index+2][4] + "residential movement " + str(len(residential_movements)) + ", "
                    take_measurements(index, data[index][3], data[index][1])
                else:
                    if debug_find_residents:
                        print("Ignored corrected movement: " + str(data[index]))
        return
    
    
    # STATISTICS
    
    # read CSV
    with open(csv_file_name) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        for row in csv_reader:
            # print(f"At {row[0]}, bee {row[1]} did {row[2]} from/to nest {row[3]}.")
            if (row[1] == '?'): continue
            data.append([row[0], row[1], row[2], row[3], ""])
            # print(data[line_count])
            line_count += 1
        # print(f'Processed {line_count} lines.')

    
    # sort by bee
    data.sort(key=lambda x: (x[1],x[0]))
    
    # bee-based error check: check if leave for every enter of each bee's movements exists
    bee_index = 0
    for line in data:
        if len(data) < 2:
            break
        next_line = data[bee_index + 1]
        # check if next line is still about the same bee
        if line[1] == next_line[1]:
            # check for enter without leave (and vice versa)
            if line[2] == "Enter" and (next_line[2] != "Leave" or next_line[3] != line[3]):
                errors.append([line, "missing enter or leave of bee " + str(line[1])])
                correct_missing_movement(bee_index, "bee-based")
            if "Leave" in line[2] and (next_line[2] != "Enter"):
                errors.append([line, "missing enter or leave of bee " + str(line[1])])
                correct_missing_movement(bee_index, "bee-based")
            # movement seems valid, check if resident
            # else:
            #     check_resident(bee_index)
        bee_index += 1
        if bee_index >= len(data) - 1:
            break
    
    
    # find residences (a separate for loop is used for clarity)
    bee_index = 0
    for line in data:
        if len(data) < 3:
            break
        # check if next two lines are still about the same bee
        if line[1] == data[bee_index + 1][1] == data[bee_index + 2][1]:
            check_resident(bee_index)
        bee_index += 1
        if bee_index == len(data) - 2:
            break
    
    # sort  residential movements by nests to prepare for creation of address book
    residential_movements.sort(key=lambda x: (x[0],x[1]))
    
    # create address book from residential movements
    for movement in residential_movements:
        # check for duplicate movements
        found = False
        for index,address in enumerate(address_book):
            if address[0] == movement[0] and address[1] == movement[1]:
                found = True
                address_book[index] = [movement[0],movement[1],address[2] + 1]
        if not found:
            address_book.append([movement[0],movement[1],1])
    
    # check if a nest is used by more than one bee
    address_index = 0
    for outer in address_book:
        address_count = 0
        # count how often address appears in address book
        for inner in address_book:
            if outer[0] == inner[0]:
                address_count += 1
        if address_count > 1:
            multi_nests.append(outer[0])
            multi_residents.append(outer[1])
        address_index += 1
        if address_index == len(residential_movements) - 1:
            break
    
    # nests used by more than one bee may not be counted for the address book
    for multi_nest in multi_nests:
        for address in address_book:
            if address[0] == multi_nest:
                if debug_multi_residents: print("removed an address due to multi resident: " + str(address))
                address_book.remove(address)
    
    # bees using a nest together with another bee may not be counted for flight book
    for multi_resident in multi_residents:
        for flight in flight_book:
            if flight[1] == multi_resident:
                if debug_multi_residents: print("removed a flight due to multi resident: " + str(flight))
                flight_book.remove(flight)
    
    # DATA OUTPUT

    if debug_show_error_list:
        print("\nErrors:")
        print(*errors, sep="\n")
    
    if debug_multi_residents:
        print("\nMulti nests:")
        print(*multi_nests, sep="\n")
    
    if debug_multi_residents:
        print("\nMulti residents:")
        print(*multi_residents, sep="\n")

    # sort again by time
    data.sort(key=lambda x: x[0])

    error_corrected_event_list_csv = os.path.join(output_folder,"error_corrected_events.csv")
    if os.path.exists(error_corrected_event_list_csv):
        os.remove(error_corrected_event_list_csv)
    with open(error_corrected_event_list_csv, 'a') as f:
        f.write("TIME,BEE_ID,MOVEMENT,CAVITY_ID,USED\n")
        for line in data:
            if len(line) > 4:
                f.write(str(line[0]) + ", " + str(line[1]) + ", " + str(line[2])+ ", " + str(line[3])+ ", " + str(line[4]) + "\n")
            else:
                f.write(str(line[0]) + ", " + str(line[1]) + ", " + str(line[2])+ ", " + str(line[3]) + "\n")
   
    address_book_csv = os.path.join(output_folder,"address_book.csv")
    if os.path.exists(address_book_csv):
        os.remove(address_book_csv)
    with open(address_book_csv, 'a') as f:
        f.write("BEE_ID,CAVITY_ID,EVIDENCE\n")
        for address in address_book:
            f.write(str(address[1]) + ", " + str(address[0]) + ", " + str(address[2]) + "\n")
    
    boozer_book_csv = os.path.join(output_folder,"nest_recognition.csv")
    if os.path.exists(boozer_book_csv):
        os.remove(boozer_book_csv)
    with open(boozer_book_csv, 'a') as f:
        f.write("TIME,BEE_ID,CAVITIES\n")
        for shamble in boozer_book:
            f.write(str(shamble[0]) + ", " + str(shamble[1]) + ", " + str(shamble[2])+ "\n")
    
    flight_list_csv = os.path.join(output_folder,"flight_list.csv")
    if os.path.exists(flight_list_csv):
        os.remove(flight_list_csv)
    with open(flight_list_csv, 'a') as f:
        f.write("TIME,BEE_ID,DURATION\n")
        for flight in flight_book:
            f.write(str(flight[0]) + ", " + str(flight[1]) + ", " + str(flight[2][0]) + ":" + str(flight[2][1])+ "\n")
            
if __name__ == '__main__':
    for file in os.listdir("/Users/ubique/Downloads/csvFiles"):
        if "unfiltered" in file:
            csv_file_name = "/Users/ubique/Downloads/csvFiles/" + file
            output_folder = "/Users/ubique/Downloads/csvFiles"
            extract_agroscope_metrics(csv_file_name, output_folder)
            print(csv_file_name[-10:])
            os.rename("/Users/ubique/Downloads/csvFiles/error_corrected_events.csv","/Users/ubique/Downloads/csvFiles/error_corrected_events" + csv_file_name[-10:])


    