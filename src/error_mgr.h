#pragma once

#include <csetjmp>
#include <string>

#include "lib/jpegli/common.h"

namespace ajpegli {

struct ErrorManager {
  jpeg_error_mgr pub;
  jmp_buf jump_buffer;
  std::string message;
};

jpeg_error_mgr* SetupErrorManager(ErrorManager* err);

}  // namespace ajpegli

