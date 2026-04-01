from PySpice.Spice.Netlist import Circuit, SubCircuit, SubCircuitFactory
from PySpice.Unit import *
import os
os.environ["path"] += os.pathsep + r"C:\Python38\lib\site-packages\PySpice\Spice\NgSpice\Spice64_dll\dll-vs"

circuit = Circuit("BTJ Amplifier")

circuit.model('2N3904', 'NPN',
    IS=1e-14,      # Saturation current
    VAF=100,       # Early voltage
    BF=300,        # Forward beta
    IKF=0.4,       # High-current effect coefficient
    XTB=1.5,       # Base-width effect
    BR=4,          # Reverse beta
    CJC=4e-12,     # Collector-base junction capacitance
    CJE=8e-12,     # Emitter-base junction capacitance
    RB=20,         # Base resistance
    RC=0.1,        # Collector resistance
    RE=0.1,        # Emitter resistance
    TR=250e-9,     # Carrier transit time
    TF=350e-12,    # Forward diffusion time
    ITF=1,         # Forward current dependence coefficient
    VTF=2,         # Forward transit voltage
    XTF=3,         # Forward transit exponent
    VCE0=40,       # Collector-emitter breakdown voltage
    IKRATING=0.2   # Max collector current (200 mA)
)
circuit.model('1N5819', 'D',
    IS=31.7e-6,       # Saturation current (Is=31.7u)
    RS=0.051,         # Series resistance
    N=1.373,          # Emission coefficient
    CJO=110e-12,      # Zero-bias junction capacitance
    M=0.35,           # Grading coefficient
    EG=0.69,          # Bandgap voltage
    XTI=2,            # Temperature coefficient exponent
    IAVE=1,           # Average forward current (not always used in simulations)
    VPK=40            # Peak reverse voltage (optional, mainly for transient/stress)
)
class BPF(SubCircuit):
    __nodes__ = ('In', 'Out')
    def __init__(self, name, L=10@u_uH, C=100@u_pF):
        SubCircuit.__init__(self, name, *self.__nodes__)
        self.L(1, 'In', 'Out', L)
        self.C(1, 'Out', circuit.gnd, C)




class Diode_Ring_Mixer(SubCircuit):
    __nodes__ = ('RF_In', 'LO_In', 'IF_Out')
    def __init__(self, name, LComm=33@u_uH):
        SubCircuit.__init__(self, name, *self.__nodes__)
        # RF 
        self.L(5, 'RF_In', circuit.gnd, LComm)
        self.L(1, 'TopRing', circuit.gnd, LComm)
        self.L(2, circuit.gnd, 'BottomRing', LComm)
        self.K('K_L5_L1', '5', '1', 1)
        self.K('K_L5_L2', '5', '2', 1)
        self.K('K_L1_L2', '1', '2', 1)
        # LO
        self.L(3, 'IF_Out', 'LeftRing', LComm)
        self.L(4, 'RightRing', 'IF_Out', LComm)
        self.L(6, 'LO_In', circuit.gnd, LComm)
        self.K('K_L3_L4', '3', '4', 1)
        self.K('K_L3_L6', '3', '6', 1)
        self.K('K_L4_L6', '4', '6', 1)
        """
        # N007 = LEFTRING
        # N008 = TOPRING
        # N016 = RIGHTRING
        # N017 = BOTTOMRING
        
        L5 N008 0 33µ Rser=1m 
        L6 0 N017 33µ Rser=1m 

        L7 AF N007 33µ Rser=1m 
        L8 N016 AF 33µ Rser=1m 

        These are the inputs 
        L10 RF 0 33µ Rser=1m 
        L13 OSC 0 33µ Rser=1m"""

        # Diodes
        self.D(2, 'LeftRing', 'TopRing', model='1N5819')
        self.D(1, 'TopRing', 'RightRing', model='1N5819')
        self.D(3, 'BottomRing', 'LeftRing', model='1N5819')
        self.D(4, 'RightRing', 'BottomRing', model='1N5819')
        """D2 N007 N008 1N5819 
        D1 N008 N016 1N5819 
        D3 N017 N007 1N5819 
        D4 N016 N017 1N5819 """


class BJT_CE(SubCircuit):
    __nodes__ = ('Vin', 'VBB', 'C')

    def __init__(self, name, R1=100@u_kOhm, R2=20@u_kOhm, Re=1300@u_Ohm, Rc=5@u_kOhm, C1=100e-6@u_F):
        SubCircuit.__init__(self, name, *self.__nodes__)
        Vcc = 12@u_V
        self.V('VDD', 'VDD', self.gnd, Vcc)
        self.R(1, 'VBB', 'B', R1)
        self.R(2, 'B', self.gnd, R2)
        self.R(3, 'C', 'VDD', Rc)
        self.R(4, 'E', self.gnd, Re)
        self.C(1, 'Vin', 'B', C1)
        self.Q('Q1', 'C', 'B', 'E', model='2N3904')

class BJT_Colpitts(SubCircuit):
    __nodes__ = ('Vcc', 'LC_In', 'C', 'E')

    def __init__(self, name, R1=20@u_kOhm, R2=10@u_kOhm, Re=3@u_kOhm, Cc=10@u_nF, Fcap=10@u_nF,
                 Rc=5.9@u_kOhm, C1=810@u_pF, C2=810@u_pF, L1=1@u_uH):
        SubCircuit.__init__(self, name, *self.__nodes__)
        Vcc = 12@u_V
        # Divider Bias and VCC
        self.V('VCC', 'VCC', self.gnd, Vcc)
        self.R(1, 'VCC', 'B', R1)
        self.R(2, 'B', self.gnd, R2)
        # Collector Resistor
        self.R('Rc', 'C', 'VCC', Rc)
        self.C('Cc', 'C', 'LC_In', Cc)
        # Emitter Resistor + Capitor
        self.R(3, 'E', self.gnd, Re)
        # self.C('Ce', 'E', self.gnd, Ce)
        # LC Tank
        self.C(1, 'LC_In', self.gnd, C1, initial_condition=0.001@u_V)
        self.C(2,  self.gnd, 'FCap', C2, initial_condition=0@u_V)
        self.L(1, 'LC_In', 'FCap', L1, initial_condition=0.01@u_V)
        # Feedback Cap
        self.C(3, 'FCap', 'B', Fcap)
        self.R('Rshunt', 'LC_In', self.gnd, 1@u_MOhm)
        # Transistor
        self.Q('Q1', 'C', 'B', 'E', model='2N3904')


class BJT_CE_Bypassed(SubCircuit):
    __nodes__ = ('Vin', 'VBB', 'C')

    def __init__(self, name, R1=100@u_kOhm, R2=20@u_kOhm, Re=1300@u_Ohm, Rc=5@u_kOhm, C1=100e-6@u_F):
        SubCircuit.__init__(self, name, *self.__nodes__)
        Vcc = 12@u_V
        self.V('VDD', 'VDD', self.gnd, Vcc)
        self.R(1, 'VBB', 'B', R1)
        self.R(2, 'B', self.gnd, R2)
        self.R(3, 'C', 'VDD', Rc)
        self.R(4, 'E', self.gnd, Re)
        self.C(1, 'Vin', 'B', C1)
        self.Q('Q1', 'C', 'B', 'E', model='2N3904')
        self.C(2, 'E', self.gnd, 100e-9@u_F)

class BJT_SF(SubCircuit):
    __nodes__ = ('B', 'E')
    def __init__(self, name, Re=1000@u_Ohm):
        SubCircuit.__init__(self, name, *self.__nodes__)
        Vcc = 12@u_V
        self.V('VDD', 'C', self.gnd, Vcc)
        self.R(4, 'E', self.gnd, Re)
        self.Q('Q1', 'C', 'B', 'E', model='2N3904')

class Audio_Diplexer(SubCircuit):
    __nodes__ = ('Audio_In', 'Audio_Out')
    def __init__(self, name, L=100@u_uH, C=0.47@u_uF):
        SubCircuit.__init__(self, name, *self.__nodes__)
        self.L(1, 'Audio_In', 'Audio_Out', L)
        self.C(1, 'Audio_Out', circuit.gnd, C)
        self.C(2, 'Audio_In', 'RTop', 100@u_nF)
        self.R(1, 'RTop', circuit.gnd, 50@u_Ohm)

circuit.subcircuit(BJT_CE('RF_Amp'))
circuit.subcircuit(BJT_SF('Post_RF_Buffer'))
circuit.subcircuit(BJT_SF('Pre_RF_Buffer'))
circuit.subcircuit(BJT_Colpitts('Colpitts_Osc'))
circuit.subcircuit(Diode_Ring_Mixer('Mixer'))
circuit.subcircuit(Audio_Diplexer('Diplexer'))




circuit.V(1, 'Source', circuit.gnd, 'SINE(0 0.000001 7102000)')
circuit.R(1, 'Source', 'RF_Out', 1@u_Ohm)
circuit.X(1, 'Colpitts_Osc', 'VDD', 'LC_In', 'C', 'E')
circuit.X(2, 'Post_RF_Buffer', 'C', 'BufferOut')
circuit.X(3, 'Mixer', 'RF_Out', 'BufferOut', 'IF_Out')
circuit.R(2, 'IF_Out', 'Audio', 1@u_kOhm)
circuit.C(1, 'Audio', circuit.gnd, 100e-6@u_F)
# circuit.X(4, 'Diplexer', 'Audio', 'Audio_Out')

print(str(circuit))

# AC voltage source at test node
import matplotlib.pyplot as plt
import numpy as np
from scipy.fft import fft, fftfreq
from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import *

# --- Transient Simulation ---
simulator = circuit.simulator(temperature=25, nominal_temperature=25)

# Small step time to resolve MHz oscillation, total 1 ms
analysis = simulator.transient(step_time=0.005@u_us, end_time=30@u_ms)

# --- Extract time-domain waveform ---
time = np.array(analysis.time)
voltage = np.array(analysis['IF_Out'])  # oscillator output node

# --- Plot time-domain waveform ---
plt.figure()
plt.plot(time, voltage)
plt.xlabel('Time [s]')
plt.ylabel('Voltage [V]')
plt.title('Oscillator Output (Time Domain)')
plt.grid(True)
plt.show()

# Take last 50% of waveform to avoid startup
start_idx = int(len(time)*0.75)
voltage = voltage[start_idx:]
time = time[start_idx:]

# FFT
N = len(time)
dt = float(time[1] - time[0])
V_fft = fft(voltage)
freqs = fftfreq(N, dt)

idx = np.where(freqs > 0)
freqs = freqs[idx]
V_fft = V_fft[idx]


# Find peak frequency
peak_freq = freqs[np.argmax(np.abs(V_fft))]
print(f'Oscillator frequency ≈ {peak_freq/1e6:.3f} MHz')

# --- Plot frequency spectrum ---
plt.figure()
plt.plot(freqs/1e6, 20*np.log10(np.abs(V_fft)))
plt.xlabel('Frequency [MHz]')
plt.ylabel('Magnitude [dB]')
plt.title('Oscillator Frequency Spectrum')
plt.grid(True)
plt.show()



# circuit.V(1, 'Vin', circuit.gnd, 0@u_V)
# circuit.V(1, 'Vin', circuit.gnd, 'SINE(0 1 1k)')
# Antenna
# Divider + Ant Coupler
"""circuit.R(1, 'VBB', 'Pre_RF_Buffer', 10@u_kOhm)
circuit.R(2, 'Pre_RF_Buffer', circuit.gnd, 10@u_kOhm)
circuit.C(1, 'Pre_RF_Buffer', 'RF_Input', 100e-6@u_F)
circuit.V(3, 'RF_Input', circuit.gnd, "SINE(0 1 7000000)")
# Input Buffer
circuit.X(1, 'Pre_RF_Buffer', 'RF_Input', 'BufferOut1')
# RF Amplifier
circuit.X(2, 'RF_Amp', 'BufferOut2', 'VBB', 'Vout')
# Output Buffer
circuit.X(3, 'Post_RF_Buffer', 'Vout', 'BufferOut2')
"""