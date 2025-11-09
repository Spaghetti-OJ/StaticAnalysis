#include "misc/ForbidArraysCheck.h"
#include "clang/ASTMatchers/ASTMatchFinder.h"

using namespace clang::ast_matchers;

namespace clang::tidy::misc {

void ForbidArraysCheck::registerMatchers(MatchFinder *Finder) {
  // Match any variable declared with an array type.
  Finder->addMatcher(varDecl(hasType(arrayType())).bind("arr"), this);
}

void ForbidArraysCheck::check(const MatchFinder::MatchResult &Result) {
  const auto *Arr = Result.Nodes.getNodeAs<VarDecl>("arr");
  if (!Arr)
    return;
  diag(Arr->getBeginLoc(), "Array declaration is forbidden.");
}

} // namespace clang::tidy::misc
