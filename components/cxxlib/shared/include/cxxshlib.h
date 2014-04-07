
#ifdef _MSC_VER
#define FREGGELSPEC	__declspec(dllexport)
#else
#define FREGGELSPEC
#endif

class FREGGELSPEC Shared
{
public:
	Shared() {}
	double add(double x, double y);
};
