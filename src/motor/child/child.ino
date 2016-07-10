#include <EEPROM.h>

// identity
String id = "";

// variables
int LED = 13;

// version number
String version_number = "0.1";

// is streaming?
bool stream = false;

// encoder pins
int encoderA = 2;
int encoderB = 4;

// encoder position
volatile unsigned int encoderPos = 0;

// the setup function runs once when you press reset or power the board
void setup() {
  Serial.begin(9600);
  pinMode(LED, OUTPUT);

  // setup encoder pins and turn on internal pull-up resistor
  pinMode(encoderA, INPUT);
  digitalWrite(encoderA, HIGH);

  pinMode(encoderB, INPUT);
  digitalWrite(encoderB, HIGH);

  // attach interrupt to keep track of posittion
  attachInterrupt(digitalPinToInterrupt(encoderA), updateEncoderPos, CHANGE);
  
  id = rememberID();
}

void updateEncoderPos() {
  
}

void serialEvent() {
  if (Serial.available() && !stream) {
    String symbol = Serial.readStringUntil(' ');
    String command = Serial.readStringUntil(' ');
    String info = Serial.readStringUntil('\n');
    receivedMessage(symbol, command, info);
    // digitalWrite(LED, HIGH);
    // delay(500);
    // digitalWrite(LED, LOW);
  }
}

void receivedMessage(String symbol, String command, String info) {  
//  if (symbol == "?") {
//    if (command == "listen") {
//      Serial.println(estResponse);
//      
//    } 
//    
//    else if (command == "id") {
//      Serial.println("$ id " + id);
//    }
//  }
//  
//  if (symbol == "!") {
//    if (command == "id") {
//      id = info;
//      setID(info);
//      Serial.println("# id " + info);
//    }
//  }

  if (command == "version") {
    Serial.println("$ version " + version_number);
  }

  else if (command == "id") {
    if (symbol == "?") { // asking for id
      Serial.println("$ id " + id);
    } 
    
    else if (symbol == "!") { // set id
      id = info;
      setID(info);
      Serial.println("# id " + info);
    }
  }

  else if (command == "step") {
    if (symbol == "!") { // move and open data stream
      stream = true;
      Serial.println("> step " + info);
      for (int i = 0; i < info.toInt(); i++) {
        Serial.println(i);
        // delay(200);
      }
      Serial.println("/ step " + info);
      stream = false;
    }
  }
}

String rememberID() {
  char value;
  int address = 0;
  String id = "";
  while (true) { // loop
    value = EEPROM.read(address);
    
    if (value != 0) { // value is not null
      id += value;
    } else {
      break;
    }
    
    address++;
  }
  
  return id;
}

void setID(String id) {
  clearMem();
  for (int i = 0; i < id.length(); i++) {
    EEPROM.write(i, id[i]);
  }
}

void clearMem() {
  for (int i = 0 ; i < EEPROM.length() ; i++) {
    EEPROM.write(i, 0);
  }  
}

int address = 0;
byte value;
boolean l = true;

// the loop function runs over and over again forever
void loop() {

}


