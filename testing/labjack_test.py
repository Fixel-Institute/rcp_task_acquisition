

'''
Test to check if labjack data looks correct- update with the correct file and will create a plot based on the data
use the keyboard to move through the points
'''
import csv

import matplotlib.pyplot as plt
import numpy as np
from pynput.keyboard import Key, Listener

def graph_csv():
    with open('/media/rld/c87215a7-5f3c-4acf-bb4d-2b823140e003/RawDataLocal/20260317/unitME/session005/20260317_unitME_session005_labjack.txt', 'r') as csvfile:
        test_dict = {"PHOTODIODE": [],
         "CAMERA": []}
        reader = csv.reader(csvfile)
        for index,row in enumerate(reader):

            # if index!=0:
            try:
                test_dict["CAMERA"].append(float(row[-1]))
                test_dict["PHOTODIODE"].append(float(row[4]))
            except:
                pass

    return test_dict

step = 100000

start = 100

end = start+step

def run_graph():
    graph_dict = graph_csv()
    global start
    global end

    
    
    y_values = graph_dict["CAMERA"][start:end]
    
    digital = np.array(y_values, dtype=np.uint8)
    # print(digital)
    digital_reshape =np.unpackbits( digital.view(np.uint8)).reshape(8, len(y_values), order = "F")[::-1]
    new_y = digital_reshape[6]
    
    x_values = np.arange(start, end)
    plt.plot(x_values, new_y)
    
    
    
    # Display the plot
    plt.show()
    
    start+=step 
    end+=step            
    
    
def on_press(key):
    global step
    run_graph()

def on_release(key):
    print('{0} release'.format(
        key))
    if key == Key.esc:
        # Stop listener
        return False

# Collect events until released
with Listener(
        on_press=on_press,
        on_release=on_release) as listener:
    listener.join()


with Listener(
        on_press=on_press,
        on_release=on_release) as listener:
    listener.join()

