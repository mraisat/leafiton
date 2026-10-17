const int LIGHT_PIN = A0;          // photoresistor on A0
const int PIR_PIN = 2;             // PIR output on digital pin 2
const int LED_PIN = 7;             // demo "room light" LED on pin 7
const int BUZZER_PIN = 8;          // buzzer on pin 8
const int LIGHT_THRESHOLD = 350;   // above this = lights on
const unsigned long NO_MOTION_LIMIT = 10000; // 10 seconds for testing

unsigned long lastMotionTime = 0;  // when we last saw motion

void setup() {
  Serial.begin(9600);              // start serial at 9600 baud
  pinMode(PIR_PIN, INPUT);         // PIR is an input
  pinMode(LED_PIN, OUTPUT);        // LED is an output
  pinMode(BUZZER_PIN, OUTPUT);     // buzzer is an output
}

void loop() {
  int light = analogRead(LIGHT_PIN);          // read light level
  bool lightsOn = light > LIGHT_THRESHOLD;    // are the lights on?
  bool motion = digitalRead(PIR_PIN) == HIGH; // is someone moving?

  if (motion) {
    lastMotionTime = millis();     // reset the timer on motion
  }

  unsigned long stillTime = millis() - lastMotionTime; // ms since last motion
  bool waste = lightsOn && stillTime > NO_MOTION_LIMIT; // lights on + empty room

  digitalWrite(LED_PIN, waste ? LOW : HIGH); // LED off when wasting

  // send one line for the Pi: DATA,light,lightsOn,motion,stillSeconds,waste
  Serial.print("DATA,");
  Serial.print(light);
  Serial.print(",");
  Serial.print(lightsOn ? 1 : 0);
  Serial.print(",");
  Serial.print(motion ? 1 : 0);
  Serial.print(",");
  Serial.print(stillTime / 1000);
  Serial.print(",");
  Serial.println(waste ? 1 : 0);

  if (waste) {
    digitalWrite(BUZZER_PIN, HIGH); // buzzer on
    delay(100);                     // short beep
    digitalWrite(BUZZER_PIN, LOW);  // buzzer off
  }

  delay(500);                       // send twice a second
}
