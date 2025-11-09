#include "misc/ForbidLoopsCheck.h"
#include "clang/ASTMatchers/ASTMatchFinder.h"

using namespace clang::ast_matchers;

namespace clang::tidy::misc {

void ForbidLoopsCheck::registerMatchers(MatchFinder *Finder) {
  Finder->addMatcher(stmt(anyOf(forStmt(), whileStmt(), doStmt())).bind("loop"), this);
}

void ForbidLoopsCheck::check(const MatchFinder::MatchResult &Result) {
  const Stmt *Loop = Result.Nodes.getNodeAs<Stmt>("loop");
  if (!Loop)
    return;
  diag(Loop->getBeginLoc(), "Loop statements (for/while/do) are forbidden.");
}

} // namespace clang::tidy::misc
