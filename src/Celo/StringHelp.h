#ifndef STRINGHELP_H
#define STRINGHELP_H

#include <iostream>

#define PRINT( A ) \
    std::cout << "  " << #A << " -> " << (A) << std::endl
#define PRINTN( A ) \
    std::cout << "  " << #A << " ->\n" << (A) << std::endl

inline bool is_a_number( char a ) { return a >= '0' and a <= '9'; }


#endif // STRINGHELP_H