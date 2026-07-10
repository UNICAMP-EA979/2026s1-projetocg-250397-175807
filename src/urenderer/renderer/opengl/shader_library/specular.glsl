#ifndef LIBRARY_SPECULAR

#define PI 3.14159265359

//Calcula a refletância especular da superfície utilizando o modelo de Blinn-Phong
vec3 specularReflectance(vec3 fresnel, vec3 normal, vec3 halfAngle, vec3 viewDirection, vec3 LightDirection, float roughness)
{
    const float MAX_SHININESS = 8192.0;
    float smoothness = 1.0 - roughness;
    float alphaP = pow(MAX_SHININESS, smoothness);

    float NdotM = max(dot(normal, halfAngle), 0.0);
    float NdotL = max(dot(normal, LightDirection), 0.0001);
    float NdotV = max(dot(normal, viewDirection), 0.0001);

    float normalizationTerm = (alphaP + 2.0) / (8.0 * PI);
    float specularTerm = pow(NdotM, alphaP);

    return fresnel * normalizationTerm * specularTerm / (NdotL * NdotV);
}

#define LIBRARY_SPECULAR
#endif