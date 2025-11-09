#include "misc/ForbidSTLCheck.h"
#include "clang/ASTMatchers/ASTMatchFinder.h"

using namespace clang::ast_matchers;

namespace clang::tidy::misc {

void ForbidSTLCheck::registerMatchers(MatchFinder *Finder) {
  // Match any declaration or reference from std namespace
  // This includes std::vector, std::string, std::cout, std::sort, etc.
  Finder->addMatcher(
      declRefExpr(to(decl(isInStdNamespace()))).bind("stl_ref"),
      this);
  
  // Match variable declarations using std types (e.g., std::vector<int> v;)
  Finder->addMatcher(
      varDecl(hasType(qualType(hasDeclaration(decl(isInStdNamespace()))))).bind("stl_var"),
      this);
  
  // Match type aliases and typedefs from std
  Finder->addMatcher(
      typedefNameDecl(hasType(qualType(hasDeclaration(decl(isInStdNamespace()))))).bind("stl_typedef"),
      this);
}

void ForbidSTLCheck::check(const MatchFinder::MatchResult &Result) {
  // Check for std reference
  if (const auto *Ref = Result.Nodes.getNodeAs<DeclRefExpr>("stl_ref")) {
    diag(Ref->getBeginLoc(), "Use of STL (Standard Template Library) is forbidden.");
    return;
  }
  
  // Check for std type declaration
  if (const auto *Var = Result.Nodes.getNodeAs<VarDecl>("stl_var")) {
    diag(Var->getBeginLoc(), "Use of STL (Standard Template Library) type is forbidden.");
    return;
  }
  
  // Check for std typedef
  if (const auto *Typedef = Result.Nodes.getNodeAs<TypedefNameDecl>("stl_typedef")) {
    diag(Typedef->getBeginLoc(), "Use of STL (Standard Template Library) type is forbidden.");
    return;
  }
}

} // namespace clang::tidy::misc
