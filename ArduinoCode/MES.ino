#include <ESP8266WiFi.h>
#include <FirebaseESP8266.h>
#include <Servo.h>
#include <time.h> 

// 1. Kredensial Wi-Fi
#define WIFI_SSID "nama"
#define WIFI_PASSWORD "pass"

// 2. Kredensial Firebase
#define FIREBASE_HOST "mesku-5860d-default-rtdb.firebaseio.com" 
#define FIREBASE_AUTH "Rz0W3BfzJ6BQd4ZHsc59VR0rkFacLTBWfj26uRB4"

FirebaseData firebaseData;
FirebaseAuth auth;
FirebaseConfig config;

// 3. Konfigurasi Servo
Servo myServo;
const int servoPin = 12; // Pin D6 / GPIO 12

// 4. Pelacak Waktu (Diubah menjadi penghitung porsi)
int porsiPagi = 0;  // Rentang 05:00 - 09:59 (Maks 30)
int porsiSiang = 0; // Rentang 10:00 - 14:59 (Maks 30)
int porsiSore = 0;  // Rentang 15:00 - 20:59 (Maks 30)
int hariTerakhir = -1; 

void setup() {
  Serial.begin(9600); 
  
  // Koneksi ke Wi-Fi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
  
  // Koneksi ke Firebase
  config.database_url = FIREBASE_HOST;
  config.signer.tokens.legacy_token = FIREBASE_AUTH;
  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);

  // Minta waktu dari internet (NTP Server UTC+7)
  configTime(7 * 3600, 0, "pool.ntp.org", "time.nist.gov");

  Serial.println("\n[Sistem Siap] Menunggu sinyal 'F' dari Python...");
}

void loop() {
  time_t now = time(nullptr);
  struct tm* p_tm = localtime(&now);

  if (p_tm == nullptr) {
    delay(500);
    return;
  }

  int jamSekarang = p_tm->tm_hour;
  int tanggalSekarang = p_tm->tm_mday;

  // Reset kuota porsi harian tiap tengah malam
  if (tanggalSekarang != hariTerakhir && p_tm->tm_year > 100) { 
    porsiPagi = 0;
    porsiSiang = 0;
    porsiSore = 0;
    hariTerakhir = tanggalSekarang;
  }

  if (Serial.available() > 0) {
    char data = Serial.read();
    
    if (data == 'F') {
      if (p_tm->tm_year < 100) {
        Serial.println("Waktu belum sinkron, silakan tunggu sebentar dan coba lagi...");
        while(Serial.available() > 0) Serial.read(); // Kuras antrean
        return; 
      }

      bool izinkanMakan = false;
      String namaSlot = "";
      int porsiKe = 0;

      // Logika Jadwal (Batas maksimal 30 kali per rentang)
      if (jamSekarang >= 5 && jamSekarang < 10 && porsiPagi < 30) {
        izinkanMakan = true;
        porsiPagi++;
        porsiKe = porsiPagi;
        namaSlot = "Pagi (05:00-10:00)";
      } 
      else if (jamSekarang >= 10 && jamSekarang < 15 && porsiSiang < 30) {
        izinkanMakan = true;
        porsiSiang++;
        porsiKe = porsiSiang;
        namaSlot = "Siang (10:00-15:00)";
      } 
      else if (jamSekarang >= 15 && jamSekarang < 21 && porsiSore < 30) {
        izinkanMakan = true;
        porsiSore++;
        porsiKe = porsiSore;
        namaSlot = "Sore (15:00-21:00)";
      }

      // Eksekusi Pemberian Makan
      if (izinkanMakan) {
        Serial.print("Akses diterima! Mengeluarkan porsi ke-");
        Serial.print(porsiKe);
        Serial.println(" / 30");
        
        // Membuka katup 1x saja per sinyal
        myServo.attach(servoPin, 500, 2500);
        myServo.write(60);  
        delay(300); 
        myServo.write(0);
        delay(300); 
        myServo.detach(); 
        
        // Pembuatan Format Waktu
        char timeString[30];
        sprintf(timeString, "%04d-%02d-%02d %02d:%02d:%02d", p_tm->tm_year + 1900, p_tm->tm_mon + 1, p_tm->tm_mday, jamSekarang, p_tm->tm_min, p_tm->tm_sec);

        // Path Firebase
        String pathFirebase = "/RiwayatMakan/" + String((unsigned long)now); 
        
        // Simpan ke Firebase dengan informasi porsi ke-berapa
        String statusText = "Berhasil (Porsi ke-" + String(porsiKe) + "/30)";
        Firebase.setString(firebaseData, pathFirebase + "/waktu_lengkap", timeString);
        Firebase.setString(firebaseData, pathFirebase + "/rentang_waktu", namaSlot);
        Firebase.setString(firebaseData, pathFirebase + "/status", statusText);

        Serial.print("Sukses mencatat ke Firebase pada: ");
        Serial.println(timeString);
      } 
      else {
        Serial.println("DITOLAK: Kuota 30 kali di rentang ini sudah habis, atau sedang di luar jadwal (05:00 - 21:00).");
      }
    }
  }

  delay(50); 
}