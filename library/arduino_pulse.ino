// Fixed-width timestamp sender for alignment

// Sends: Tssss\n once per second at 2400 baud

// ssss = 0000–3599 (seconds since start)


#include <TXOnlySerial.h>


const int outSerPin = 9;
const int outTTLA = 10;
const int outTTLB = 11;

TXOnlySerial outSerial(outSerPin); // TX

const unsigned long BAUD_RATE = 2400;
const unsigned long SEND_INTERVAL_MS = 1000;   // 1 second
const unsigned int MAX_SECONDS = 3600;   // 1 hour - 1 second

unsigned long startMillis = 0;
unsigned long lastSendMillis = 0;

unsigned int sess = 0;
unsigned int trial = 0;
unsigned int msgInt = 0;
unsigned int ser2read = 0;
unsigned int timeout = 0;
unsigned int pulseCt = 1;
unsigned int secCounter = 1;
char rxStr[20];   // // Allocate some space for the string
char inChar = -1; // Where to store the character read
static unsigned int mPos = 0; // Index into array; where to store the character
unsigned int s = 0;
bool sendingTimestamps = false;
String protocolName;
const uint32_t fixedSeed = 12345;
uint32_t rngState;


void setup() {
    pinMode(outTTLA,OUTPUT);
    digitalWrite(outTTLA, LOW); 
    pinMode(outTTLB,OUTPUT);
    digitalWrite(outTTLB, LOW); 

    Serial.begin(9600);
    outSerial.begin(BAUD_RATE);

    resetTimer();
}



void loop() {
    if (sendingTimestamps) {
        unsigned long now = millis();

        // Using subtraction like this is safe across millis() rollover.
        if ((unsigned long)(now - lastSendMillis) >= SEND_INTERVAL_MS) {
            lastSendMillis = now;
            unsigned long elapsedMs  = now - startMillis;
            sendTimestamp((unsigned int)secCounter);  // we know it fits in 1–3600
            secCounter++;

            if (secCounter > MAX_SECONDS) {
                resetTimer();
            }
        }   
    }
    // --- 2) Handle incoming serial commands ---
    handleSerialCommands();
}


uint32_t nextRandom() {
    // 32-bit linear congruential generator
    rngState = 1664525UL * rngState + 1013904223UL
    return rngState;
}


int randomPulseCount() {
    return 1 + (nextRandom() % 10);  // 1–10
}


// -------------------------------------------------------------------
// Send fixed-width timestamp: Tssss\n
// ssss = zero-padded decimal seconds (width 4)
// -------------------------------------------------------------------
void sendTimestamp(unsigned int seconds) {
    char buf[15];  // 'T' + 4 digits + '\n' + '\0' = 7
    buf[0] = 'S';   
    // Convert seconds (0–9999) to 4 decimal digits, zero-padded.
    s = sess;
    buf[3] = '0' + (s % 10); s /= 10;
    buf[2] = '0' + (s % 10); s /= 10;
    buf[1] = '0' + (s % 10); // s should now be 0 for < 1000

    buf[4] = 'T';
    // Convert seconds (0–9999) to 4 decimal digits, zero-padded.
    s = trial;
    buf[7] = '0' + (s % 10); s /= 10;
    buf[6] = '0' + (s % 10); s /= 10;
    buf[5] = '0' + (s % 10); // s should now be 0 for < 1000

    buf[8] = 'U';
    // Convert seconds (0–9999) to 4 decimal digits, zero-padded.
    s = seconds;
    buf[12] = '0' + (s % 10); s /= 10;
    buf[11] = '0' + (s % 10); s /= 10;
    buf[10] = '0' + (s % 10); s /= 10;
    buf[9] = '0' + (s % 10); // s should now be 0 for < 10000

    buf[13] = '\n';
    buf[14] = '\0';

    outSerial.print(buf);  // non-blocking enough at 2400 baud & 1 Hz
    // Serial.print(buf);  // non-blocking enough at 2400 baud & 1 Hz
    pulseCt = randomPulseCount();
    // Serial.println(seconds);
    // Serial.println(pulseCt);
    for(int x = 0; x < pulseCt; x++) {
        digitalWrite(outTTLB, HIGH);
        delay(5);
        digitalWrite(outTTLB, LOW);
        delay(5);
    }
}


void resetTimer(){
    startMillis = millis();
    lastSendMillis = startMillis;
    secCounter = 1;
    rngState = fixedSeed;
}


void readInteger(){
    timeout = 0;
    msgInt = 0;
    while (Serial.available() == 0) {
        delay(1);
        timeout += 1;

        if (timeout > 500){
            return;
        }
    }

    delay(50);
    ser2read = Serial.available();
    for(int x = 0; x < ser2read; x++) {
        if(mPos < 19){ // One less than the size of the array

            while ((ser2read-x) == Serial.available()){
                inChar = Serial.read(); // Read a character
            }

            if (inChar == 'x'){
                break;
            }

            rxStr[mPos] = inChar; // Store it
            mPos++; // Increment where to write next
        }
    }
    rxStr[mPos] = '\0'; // Null terminate the string
    mPos=0;
    msgInt = atoi(rxStr);
}


// -------------------------------------------------------------------
// Commands from the PC
// -------------------------------------------------------------------
void handleSerialCommands() {
    if (Serial.available() > 0) {
        char c = Serial.read();
        if (c == 'A') {
            for (int i = 0; i < 10; i++) {
                // Serial.println("pulse");
                digitalWrite(outTTLA, HIGH);
                delay(1);
                digitalWrite(outTTLA, LOW);
                delay(11.5);
            }
        }

        // else if (c == 'B') 
        //   digitalWrite(outTTLB, HIGH);
        //   delay(5);
        //   digitalWrite(outTTLB, LOW);
        // }

        else if (c == 'P') {
            while (Serial.available() == 0) {
                delay(1);
            }
            if (Serial.available() > 0) {
                // Read the string until a newline character ('\n') is received
                protocolName = Serial.readStringUntil('\n');
                // Serial.println(protocolName);
                outSerial.print('P'+protocolName+'\n');
            }

        }

        else if (c == 'S') {
            readInteger();
            sess = msgInt;
            readInteger();
            trial = msgInt;

            sendingTimestamps = true;
            // outSerial.print('S');
            resetTimer();
            pulseCt = 1;
        }

        else if (c == 'X') {
            // Serial.println("Stop");
            sendingTimestamps = false;
            outSerial.print('X\n');
        }
    }
}