import numpy as np
from matplotlib import pyplot as plt
from scipy.ndimage import gaussian_filter

# Data processing; you can invoke load_file and run from a shell if you just want to analyse existing data

filename = "datafile_2025-03-30_15-57.dat"
global file

def load_file(filename):
    global file
    file = open(filename, 'r')

def get_line():
  return file.readline().strip()

def get_two_values_from_line():
  vals = get_line().strip().split(" ")
  print(vals)
  return [float(vals[0]),float(vals[1])]

def run():
    user_comment = get_line()
    plate_length, plate_gap = get_two_values_from_line()
    beam_energy = float(get_line())
    motor_start = float(get_line())
    motor_step_size = float(get_line())
    voltage_min  = float(get_line())*100
    voltage_step_size = float(get_line())*100
    voltage_steps = int(get_line())+1
    position_steps = int(get_line())+1

    voltage_max = voltage_min + voltage_step_size * (voltage_steps-1)
    motor_end = motor_start + motor_step_size * (position_steps-1)

    thetaConversionConstant = plate_length * 1000 / (beam_energy * 4 * plate_gap)

    xVector = [motor_start + i * (motor_end - motor_start) / position_steps for i in range(position_steps)]
    thetaVector = [+ voltage_min + i * (voltage_max - voltage_min) / voltage_steps for i in range(voltage_steps)]

    thetaVector = [thetaVectorI * thetaConversionConstant for thetaVectorI in thetaVector]

    print("thetaVector: ", len(thetaVector))

    print("Comment: ", user_comment)
    print("Plate Gap: ", plate_gap)
    print("Plate Length: ", plate_length)
    print("Beam Energy: ", beam_energy)
    print("Start and End Positions: ", "{} - {}".format(motor_start, motor_end))
    print("Start and End Voltage: ", "{} - {}".format(voltage_min, voltage_max))
    print("Start and End Theta: ", "{} - {}".format(thetaVector[0], thetaVector[len(thetaVector) - 1]))
    print("Voltage Steps: ", voltage_steps)
    print("Position Steps: ", position_steps)

    lines = file.readlines()

    data = []

    # Each row is a different voltage, each element is a different position
    for line in lines:
      data += [list(map(float, line.strip().split(' ')))]

    sigma = 0.6 # can be an user input
    data = gaussian_filter(data, sigma)
    df = data.T
    df = gaussian_filter(df, sigma)

    # background cut
    cut = 0.3
    for j in range(position_steps):
        for i in range(voltage_steps-1):
            if (df[i,j] != 0) and (df[i-1,j] < cut*np.max(df)) and (df[i+1,j] < cut*np.max(df)):
                df[i,j] = 0

    for i in range(voltage_steps):
        for j in range(position_steps-1):
            if (df[i,j] != 0) and (df[i,j-1] < cut*np.max(df)) and (df[i,j+1] < cut*np.max(df)):
                df[i,j] = 0
    #===============================


    #RMS calculation
    xS = df.sum(axis=0) * (1/(voltage_steps))
    thetaS = df.sum(axis=1) * (1/position_steps)


    summationX = xS.sum()
    summationTheta = thetaS.sum()


    xWeighted = sum([xVector[i] * xS[i] for i in range (position_steps)]) / summationX
    thetaWeighted = sum([thetaVector[i] * thetaS[i] for i in range (voltage_steps)]) / summationTheta

    xNew = xVector - xWeighted
    thetaNew = thetaVector - thetaWeighted


    x2RMS = 2 * np.sqrt(sum([(np.square(xNew[i]) * xS[i]) for i in range(position_steps)]) * (1/summationX))
    theta2RMS = 2 * np.sqrt(sum([(np.square(thetaNew[i]) * thetaS[i]) for i in range(voltage_steps)]) * (1/summationTheta))

    summationAllValues = sum(df.sum(axis=0))

    emittance = x2RMS*theta2RMS*np.sqrt(1-np.square(np.dot(df.dot(xNew),thetaNew)/x2RMS/theta2RMS*4/summationAllValues))


    print("Emittance: " + str(emittance))

    fig0, ax0 = plt.subplots(figsize=(7, 8), facecolor = 'w', edgecolor = 'k')
    plt.contourf(xNew,thetaNew,df, 50, cmap='jet')
    ax0.set_xlabel('mm', fontsize=18)
    ax0.set_ylabel('mrad', fontsize=18)
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=20)
    calc1 = '\n'.join((r'$2y_{RMS}$ = %.1f mm' % (x2RMS, ),r'$2y^{\prime}_{RMS}$ = %.1f mrad' % (theta2RMS, ),r'$4\epsilon_{RMS}$ = %.1f $\mu$m' % (emittance, )))
    ax0.text(0.46, 0.03, calc1, transform = ax0.transAxes, color = 'w', fontsize = 18)
    plt.tight_layout()

    plt.show()
