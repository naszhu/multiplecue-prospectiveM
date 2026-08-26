import serial
import time
import statistics

PORT = "/dev/ttyACM0"
BAUD = 115200
N = 10000

ser = serial.Serial(PORT, BAUD, timeout=0.1)
time.sleep(2)

# Clear anything left in the buffers
ser.reset_input_buffer()
ser.reset_output_buffer()

times_ms = []
failures = 0
bad_responses = 0

for i in range(N):
    ser.reset_input_buffer()

    start = time.perf_counter_ns()

    ser.write(b'I')
    ser.flush()

    response = ser.readline()

    end = time.perf_counter_ns()

    if not response:
        failures += 1
        continue

    if response.strip() != b"SRB3,v1.1":
        bad_responses += 1
        continue

    times_ms.append((end - start) / 1_000_000)

print(f"Trials:        {N}")
print(f"Successful:    {len(times_ms)}")
print(f"No response:   {failures}")
print(f"Bad response:  {bad_responses}")

if times_ms:
    print(f"Mean RT:       {statistics.mean(times_ms):.3f} ms")
    print(f"Median RT:     {statistics.median(times_ms):.3f} ms")
    print(f"SD:            {statistics.stdev(times_ms):.3f} ms")
    print(f"Minimum:       {min(times_ms):.3f} ms")
    print(f"Maximum:       {max(times_ms):.3f} ms")