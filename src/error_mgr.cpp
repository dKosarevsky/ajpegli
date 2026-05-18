#include "error_mgr.h"

#include <csetjmp>

namespace ajpegli {
namespace {

void ErrorExit(j_common_ptr cinfo) {
  auto* err = reinterpret_cast<ErrorManager*>(cinfo->err);
  char buffer[JMSG_LENGTH_MAX];
  (*cinfo->err->format_message)(cinfo, buffer);
  err->message = buffer;
  longjmp(err->jump_buffer, 1);
}

}  // namespace

jpeg_error_mgr* SetupErrorManager(ErrorManager* err) {
  jpegli_std_error(&err->pub);
  err->pub.error_exit = ErrorExit;
  err->message.clear();
  return &err->pub;
}

}  // namespace ajpegli

