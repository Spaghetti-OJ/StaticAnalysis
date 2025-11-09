#pragma once

#include "clang-tidy/ClangTidyCheck.h"
#include "clang/ASTMatchers/ASTMatchFinder.h"
#include <vector>
#include <string>

namespace clang::tidy::misc {

class ForbidFunctionsCheck : public ClangTidyCheck {
public:
  ForbidFunctionsCheck(StringRef Name, ClangTidyContext *Context);

  bool isLanguageVersionSupported(const LangOptions &LangOpts) const override {
    return true; // Support all language versions
  }
  void registerMatchers(ast_matchers::MatchFinder *Finder) override;
  void check(const ast_matchers::MatchFinder::MatchResult &Result) override;
  void storeOptions(ClangTidyOptions::OptionMap &Opts) override;

private:
  std::vector<std::string> Forbidden;
  std::string ForbiddenNamesRaw;
};

} // namespace clang::tidy::misc
