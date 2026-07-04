cmake_minimum_required(VERSION 3.10)
project(swim_extractor CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# FIT SDK Library
file(GLOB FIT_SDK_SOURCES "${CMAKE_CURRENT_SOURCE_DIR}/../third_party/fit-sdk/src/*.cpp")
add_library(fit_sdk STATIC ${FIT_SDK_SOURCES})
target_include_directories(fit_sdk PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/../third_party/fit-sdk/src")

# Swim Extractor Executable
add_executable(swim swim.cpp)
target_link_libraries(swim PRIVATE fit_sdk)
target_include_directories(swim PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/../third_party/fit-sdk/src")
