#include <stdio.h>
#include <stdlib.h>
#include <math.h>

int main(int argc, char* argv[])
{
	double val;

	if (argc != 2) {
		return EXIT_FAILURE;

	}
	
	val = atof(argv[1]);
	printf("The square root of %f is: %f\n", val, sqrt(val));
	return EXIT_SUCCESS;
}

