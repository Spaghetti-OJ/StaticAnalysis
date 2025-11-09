#include "misc/ForbidFunctionsCheck.h"
#include "clang/ASTMatchers/ASTMatchFinder.h"
#include <sstream>

using namespace clang::ast_matchers;

namespace clang::tidy::misc {

ForbidFunctionsCheck::ForbidFunctionsCheck(StringRef Name, ClangTidyContext *Context)
    : ClangTidyCheck(Name, Context),
      ForbiddenNamesRaw(Options.get("ForbiddenNames", "sort")) {
  // Parse comma-separated list
  std::stringstream ss(ForbiddenNamesRaw);
  std::string item;
  while (std::getline(ss, item, ',')) {
    // Trim whitespace
    size_t start = item.find_first_not_of(" \t");
    size_t end = item.find_last_not_of(" \t");
    if (start != std::string::npos && end != std::string::npos) {
      Forbidden.push_back(item.substr(start, end - start + 1));
    }
  }
}

void ForbidFunctionsCheck::registerMatchers(MatchFinder *Finder) {
  // Create a matcher that matches calls to any of the forbidden names.
  for (const auto &Name : Forbidden) {
    Finder->addMatcher(callExpr(callee(functionDecl(hasName(Name)))).bind("call"), this);
  }
}

void ForbidFunctionsCheck::check(const MatchFinder::MatchResult &Result) {
  const auto *Call = Result.Nodes.getNodeAs<CallExpr>("call");
  if (!Call)
    return;
  
  // Get the function declaration from the call expression
  const FunctionDecl *Callee = Call->getDirectCallee();
  std::string FuncName = Callee ? Callee->getNameAsString() : "unknown";
  
  diag(Call->getBeginLoc(), "Use of forbidden function '%0'") << FuncName;
}

void ForbidFunctionsCheck::storeOptions(ClangTidyOptions::OptionMap &Opts) {
  Options.store(Opts, "ForbiddenNames", ForbiddenNamesRaw);
}

} // namespace clang::tidy::misc
