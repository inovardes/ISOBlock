/*
Background and Problem statement:

SMBus is used to communicate with the ISO Block UUT during test.  The UUT does not utilize the SMBus protocol but 
uses a combination of I2C and PMBus protocols.  The test requirments given by Ratheon demonstrate multibyte read/write
commands which are not supported on all I2C protocol variants.  The microcontroller used on the ISO Block is an MCP19119.
The datasheet shows support for SMBus higher level protocol which supports multibyte read/write commands.  However, Raytheon
has written firmware to the MCP19119 that is a mix of I2C and PMBus, as well as home-grown commands, which were not 
compataple with the SMBus data framing, such as number of stop bits in a multibyte read command.

Solution:

This small program samples the Raspberry pi I2C clock line.  When the Raspberry pi issues a multibyte read operation,
just before the read command is sent to the I2C bus, the RPi will signal to the Arduino to begin sampling the clock line.
The arduino will acitvite an interrupt and begin sampling the RPi clock line until 19 clock edges are counted.
Clock edge #19 will clock-in the acknowledge bit from the ISO Block UUT.  The transmission data prior to the
19 clock cycles represents two bytes: an address byte which includes a write bit in the 8th byte, and a command byte.
After the ISO Block UUT acknowledges the second byte, the Raspberry pi SMBus protocol will transmit a restart, which is a stop
and start bit in succession.  The slave (ISO Block UUT) does not use the SMBus protocol and does not expect a stop bit,
only a start bit is expected.  As a result, the slave stops the current transmission after receiving the the RPi's
stop bit, and then begins a new transmission on the receipt of the start bit.  The Arduino will enable a Pfet attached
to the SDA bus which will pull the SDA line up to 5V in order to mask over the stop bit which comes about 150us after the
UUT acknowledge of the first two bytes of data.  The Arduino will release the SDA (disable the I/O attached to the Pfet)
and release the SDA line, giving control back to the RPi which will transmit the start bit to the UUT.  The time it takes
the RPi to issue the stop and start bit is approximately 20us.  Thus, the Arduino must release control of the SDA bus immediately
after the rising edge of the clock is sampled.  As of 3/3/16 the Arduino response time is good but it appears that the 
clock edges are incorrectly sensed and the Arduino will either miss the stop bit or hold the SDA line high too long.
Currently this problem is overcome in the RPi test program which will just request the read operation again.
*/


#include <TimerOne.h>

int RPi_interruptPin = 4;
int lynchSDA = 5;
int sclCount = 0;
int stopCount = 0;

void setup(void)
{
  Serial.begin(9600);
  pinMode(RPi_interruptPin,  INPUT_PULLUP);
  pinMode(lynchSDA,  OUTPUT);
  digitalWrite(lynchSDA, HIGH);//HIGH is disabled
}

void loop(void)
{
  //wait for input from RPi to initialize and then enable interrupts
  boolean temp = true;//to avoid executing interrupts() command repeatedly
  while(!digitalRead(RPi_interruptPin))
  {
    if (temp)
    {
      sclCount = 0;
      stopCount = 0;
      temp = false;
      attachInterrupt(0, sclInterrupt, RISING);//interrupt attached to RPi SCL
      Serial.println("its working");
    }
  }
}

void findStopBit()
{ 
  stopCount += 1;
  //release control of SDA
  if (stopCount == 1)
  {
    digitalWrite(lynchSDA, HIGH);//HIGH is disabled
    detachInterrupt(0);//interrupt attached to RPi SCL
  }
}

void sclInterrupt()
{
  if (sclCount == 18)
  {
    detachInterrupt(0);//interrupt attached to RPi SCL
    digitalWrite(lynchSDA, LOW);//HIGH is disable
    attachInterrupt(0, findStopBit, RISING);//interrupt attached to RPi SCL
  }
  sclCount += 1;
}
