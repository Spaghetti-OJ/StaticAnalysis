#include "clang-tidy/ClangTidyModule.h"
#include "clang-tidy/ClangTidyModuleRegistry.h"
#include "misc/ForbidLoopsCheck.h"
#include "misc/ForbidArraysCheck.h"
#include "misc/ForbidFunctionsCheck.h"
#include "misc/ForbidSTLCheck.h"

using namespace clang::tidy;

namespace clang::tidy::misc {

class MiscTidyModule : public ClangTidyModule {
public:
  void addCheckFactories(ClangTidyCheckFactories &Factories) override {
    Factories.registerCheck<ForbidLoopsCheck>("misc-forbid-loops");
    Factories.registerCheck<ForbidArraysCheck>("misc-forbid-arrays");
    Factories.registerCheck<ForbidFunctionsCheck>("misc-forbid-functions");
    Factories.registerCheck<ForbidSTLCheck>("misc-forbid-stl");
  }
};

// Register the module
static ClangTidyModuleRegistry::Add<MiscTidyModule>
    X("misc-module", "Custom rules for OJ sandbox.");

} // namespace clang::tidy::misc

// This anchor is used to force the linker to link in the module
volatile int MiscModuleAnchorSource = 0;
