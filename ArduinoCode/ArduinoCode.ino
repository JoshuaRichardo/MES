#include <Servo.h>

// Inisialisasi objek servo
Servo myServo;

// Untuk Wemos D1 R1, gunakan D4 (GPIO 2)
// Ini adalah pin yang paling stabil untuk servo pada board ini
const int servoPin = 12; 

void setup() {
  // Baud rate harus 9600 agar sesuai dengan kode Python kamu
  Serial.begin(9600);    
  
  // Menghubungkan servo ke pin
  myServo.attach(servoPin);
  
  // Set posisi awal (tertutup)
  myServo.write(0);      
  
  // Indikator bahwa ESP8266 sudah siap
  Serial.println("Wemos D1 Ready. Waiting for 'F'...");
}

void loop() {
  // Cek apakah ada data masuk dari kabel USB (Python)
  if (Serial.available() > 0) {
    char data = Serial.read();
    
    // Jika menerima karakter 'F' (Feed)
    if (data == 'F') {   
      Serial.println("Sinyal 'F' Diterima! Menggerakkan Servo...");
      
      // Gerakkan servo ke 90 derajat (membuka katup makanan)
      myServo.write(180);  
      delay(1000); // Tunggu 1 detik agar makanan jatuh
      
      // Kembalikan ke posisi 0 derajat (menutup kembali)
      myServo.write(0);
      
      Serial.println("Pemberian makan selesai.");
    }
  }
}