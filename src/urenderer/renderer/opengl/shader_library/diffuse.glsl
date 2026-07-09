#ifndef LIBRARY_DIFUSE

#define PI 3.14159265359

//Calcula a refletância difusa da superfície utilizando o modelo de Lambert
vec3 diffuseReflectance(vec3 fresnel, vec3 baseColor, float metallic)
{
    return (1.0 - fresnel) * baseColor * (1.0 - metallic) / PI;
}

#define LIBRARY_DIFUSE
#endif