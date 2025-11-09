#pragma once

#include "clang-tidy/ClangTidyCheck.h"
#include "clang/ASTMatchers/ASTMatchFinder.h"

namespace clang::tidy::misc {

class ForbidLoopsCheck : public ClangTidyCheck {
public:
  ForbidLoopsCheck(StringRef Name, ClangTidyContext *Context)
      : ClangTidyCheck(Name, Context) {}
  
  bool isLanguageVersionSupported(const LangOptions &LangOpts) const override {
    return true; // Support all language versions
  }
  void registerMatchers(ast_matchers::MatchFinder *Finder) override;
  void check(const ast_matchers::MatchFinder::MatchResult &Result) override;
};

} // namespace clang::tidy::misc
