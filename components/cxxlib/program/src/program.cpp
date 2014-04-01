
#include <stdlib.h>
#include <iostream>
#include <cxxstlib.h>
#include <cxxshlib.h>

int main()
{
	Shared shlib;
	Static stlib;

	std::cout << "Static library subtract(5, 3): ";
	std::cout << stlib.subtract(5, 3) << std::endl;

	std::cout << "Shared library add(4, 5): ";
	std::cout << shlib.add(4, 5) << std::endl;

	return EXIT_SUCCESS;
}
