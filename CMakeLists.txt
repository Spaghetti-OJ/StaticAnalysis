cmake_minimum_required(VERSION 3.13)
project(MiscTidyModule LANGUAGES C CXX)

# Export compile commands for clang-tidy (-p build)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

find_package(LLVM REQUIRED CONFIG)
find_package(Clang REQUIRED CONFIG)

message(STATUS "Found LLVM ${LLVM_PACKAGE_VERSION}")
list(APPEND CMAKE_MODULE_PATH "${LLVM_CMAKE_DIR}")
include(AddLLVM)
# Include LLVM and Clang headers (some distros don't populate CLANG_INCLUDE_DIRS)
include_directories(${LLVM_INCLUDE_DIRS})
include_directories(${LLVM_INCLUDE_DIRS}/clang)
add_definitions(${LLVM_DEFINITIONS})

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fno-rtti")

set(SRC
  src/ForbidLoopsCheck.cpp
  src/ForbidArraysCheck.cpp
  src/ForbidFunctionsCheck.cpp
  src/ForbidSTLCheck.cpp
  src/RegisterModule.cpp
)

add_library(MiscTidyModule MODULE ${SRC})
target_include_directories(MiscTidyModule PRIVATE
  include
  ${LLVM_INCLUDE_DIRS}
  ${LLVM_INCLUDE_DIRS}/clang
)

# Use LLVM's module linking instead of target_link_libraries
target_link_libraries(MiscTidyModule PRIVATE
  clangTidy
  clangAST
  clangASTMatchers
  clangBasic
  clangLex
)

set_target_properties(MiscTidyModule PROPERTIES
  POSITION_INDEPENDENT_CODE ON
  PREFIX "lib"
  OUTPUT_NAME "MiscTidyModule"
  CXX_VISIBILITY_PRESET default
  VISIBILITY_INLINES_HIDDEN OFF
)
