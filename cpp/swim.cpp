#include <fstream>
#include <iostream>
#include <ctime>
#include <iomanip>
#include <filesystem>
#include <vector>
#include <set>
#include <algorithm>
#include <map>

#include "fit_decode.hpp"
#include "fit_mesg_broadcaster.hpp"
#include "fit_developer_field_description.hpp"

namespace fs = std::filesystem;

class Listener
    : public fit::MesgListener
{
public:
    struct HeartRateRecord { FIT_DATE_TIME time; FIT_UINT8 hr; };
    struct LengthData {
        FIT_UINT32 index;
        std::wstring startTimeStr;
        FIT_DATE_TIME startTime;
        FIT_DATE_TIME endTime;
        double total_elapsed_time = 0;
        double total_timer_time = 0;
        FIT_LENGTH_TYPE length_type = FIT_LENGTH_TYPE_INVALID;
        FIT_SWIM_STROKE swim_stroke = FIT_SWIM_STROKE_INVALID;
        double total_strokes = 0;
        double avg_speed = 0;
        double avg_swimming_cadence = 0;
    };

    std::vector<HeartRateRecord> hrRecords;
    std::vector<LengthData> lengths;
    std::wofstream* outStream = nullptr;

    Listener(std::wofstream& stream) : outStream(&stream) {}

    static std::wstring FormatFitTimestamp(FIT_UINT32 fitTime)
    {
        if (fitTime >= FIT_UINT32_INVALID) return L"Invalid";
        time_t unixTime = (time_t)fitTime + 631065600 - (5 * 3600);
        struct tm* timeinfo = gmtime(&unixTime);
        wchar_t buffer[80];
        if (timeinfo) {
            wcsftime(buffer, 80, L"%Y-%m-%d %H:%M:%S CST", timeinfo);
            return std::wstring(buffer);
        }
        return L"Invalid";
    }

    void OnMesg(fit::Mesg& mesg) override
    {
        if (mesg.GetName() == "record")
        {
            fit::RecordMesg record(mesg);
            if (record.IsHeartRateValid()) {
                hrRecords.push_back({record.GetTimestamp(), record.GetHeartRate()});
            }
        }
        else if (mesg.GetName() == "length")
        {
            fit::LengthMesg lengthMesg(mesg);
            LengthData ld;
            ld.index = lengthMesg.GetMessageIndex();
            
            // Try to get the timestamp directly from the message
            ld.endTime = lengthMesg.GetTimestamp();
            ld.startTime = lengthMesg.GetStartTime();
            ld.startTimeStr = FormatFitTimestamp(ld.startTime);
            
            if (lengthMesg.IsTotalElapsedTimeValid()) ld.total_elapsed_time = lengthMesg.GetTotalElapsedTime();
            if (lengthMesg.IsTotalTimerTimeValid()) ld.total_timer_time = lengthMesg.GetTotalTimerTime();
            if (lengthMesg.IsLengthTypeValid()) ld.length_type = lengthMesg.GetLengthType();
            if (lengthMesg.IsSwimStrokeValid()) ld.swim_stroke = lengthMesg.GetLengthType();
            if (lengthMesg.IsTotalStrokesValid()) ld.total_strokes = lengthMesg.GetTotalStrokes();
            if (lengthMesg.IsAvgSpeedValid()) ld.avg_speed = lengthMesg.GetAvgSpeed();
            if (lengthMesg.IsAvgSwimmingCadenceValid()) ld.avg_swimming_cadence = lengthMesg.GetAvgSwimmingCadence();

            lengths.push_back(ld);
        }
    }

    void WriteCSV()
    {
        if (lengths.empty() || !outStream) return;

        // Header
        *outStream << L"message_index\tstart_time\ttimestamp\tcalc_duration\ttotal_elapsed_time\ttotal_timer_time\tlength_type\tswim_stroke\ttotal_strokes\tavg_speed\tavg_swimming_cadence\tavg_heart_rate\n";

        // Rows
        for (const auto& ld : lengths) {
            FIT_UINT32 duration = (ld.endTime >= ld.startTime) ? (ld.endTime - ld.startTime) : 0;
            *outStream << ld.index << L"\t" << ld.startTimeStr << L"\t" 
                       << ld.endTime << L"\t"
                       << duration << L"\t"
                       << std::fixed << std::setprecision(2) << ld.total_elapsed_time << L"\t"
                       << std::fixed << std::setprecision(2) << ld.total_timer_time << L"\t"
                       << (int)ld.length_type << L"\t"
                       << (int)ld.swim_stroke << L"\t"
                       << std::fixed << std::setprecision(2) << ld.total_strokes << L"\t"
                       << std::fixed << std::setprecision(2) << ld.avg_speed << L"\t"
                       << std::fixed << std::setprecision(2) << ld.avg_swimming_cadence << L"\t";

            float hrSum = 0;
            int hrCount = 0;
            for (const auto& rec : hrRecords) {
                if (rec.time >= ld.startTime && rec.time <= ld.endTime) {
                    hrSum += rec.hr;
                    hrCount++;
                }
            }
            
            if (hrCount > 0) *outStream << std::fixed << std::setprecision(1) << (hrSum / hrCount);
            else {
                FIT_UINT8 lastHR = 0;
                FIT_UINT32 closestTime = 0;
                for (const auto& rec : hrRecords) {
                    if (rec.time <= ld.startTime && rec.time > closestTime) {
                        lastHR = rec.hr;
                        closestTime = rec.time;
                    }
                }
                if (lastHR > 0) *outStream << std::fixed << std::setprecision(1) << (float)lastHR;
                else *outStream << L"0.0";
            }
            
            *outStream << L"\n";
        }
    }
};

int main(int argc, char* argv[])
{
   std::string inputPath = ".";
   std::string outputPath = ".";
   if (argc >= 2) inputPath = argv[1];
   if (argc >= 3) outputPath = argv[2];

   if (!fs::exists(inputPath) || !fs::is_directory(inputPath)) return -1;
   if (!fs::exists(outputPath)) fs::create_directories(outputPath);

   for (const auto& entry : fs::directory_iterator(inputPath))
   {
      if (entry.path().extension() == ".fit")
      {
         std::ifstream file(entry.path().string(), std::ios::in | std::ios::binary);
         if (!file.is_open()) continue;

         std::wofstream out((fs::path(outputPath) / entry.path().filename()).replace_extension(".csv").string());
         if (!out.is_open()) continue;

         printf("Processing: %s\n", entry.path().string().c_str());

         fit::Decode decode;
         fit::MesgBroadcaster mesgBroadcaster;
         Listener listener(out);
         mesgBroadcaster.AddListener((fit::MesgListener &)listener);

         try {
            decode.Read(file, mesgBroadcaster);
            listener.WriteCSV();
         } catch (...) {}
      }
   }
   return 0;
}
