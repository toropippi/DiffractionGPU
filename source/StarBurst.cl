#define PI 3.14159265358979323846264338328

#if (DOUBLEON==1)
#define TYPE double
#else
#define TYPE float
#endif


typedef struct{
	TYPE r;
	TYPE i;
} Complex;



void hsv2rgb(TYPE hue,TYPE *red_,TYPE *green_,TYPE *blue_)
{
	if (hue<0)hue+=360.0;
	TYPE saturation = 310.0;
	TYPE value = 290.0;
	TYPE c = saturation;
	TYPE _h = hue / 60;
	TYPE tmp = fmod(_h, 2) - 1;
	if (tmp<0)tmp=-tmp;
	TYPE _x = c * (1.0 - tmp);
	TYPE red , green , blue;
	red = green = blue = value - c;
	if (_h < 1) {
		red += c;
		green += _x;
	}
	else if (_h < 2) {
		red += _x;
		green += c;
	}
	else if (_h < 3) {
		green += c;
		blue += _x;
	}
	else if (_h < 4) {
		green += _x;
		blue += c;
	}
	else if (_h < 5) {
		red += _x;
		blue += c;
	}
	else if (_h < 6) {
		red += c;
		blue += _x;
	}
	*red_=red;
	*green_=green;
	*blue_=blue;
}


__kernel void Diffraction(__global Complex *buffer,TYPE xx,TYPE yy,TYPE R,TYPE k,TYPE sx,TYPE sy)
{
	uint id = get_global_id(0);
	uint ix = id%OX;
	uint iy = id/OX;
	TYPE idx = ix;
	TYPE idy = iy;
	idx-=OX/2;
	idy-=OY/2;
	idx*=xx;
	idy*=yy;
	idx-=sx;
	idy-=sy;
	
	TYPE a1=1;
	TYPE r=sqrt(R*R+idx*idx+idy*idy);
	TYPE base_w=r*k;//k=2*PI/lambda
	TYPE r1r=1.0/r;
	for(uint i=0;i<SPLIT_N;i++)
	{
		Complex o2=buffer[ix+iy*OX+i*OX*OY];
		TYPE c=cos(base_w*a1)*r1r;
		TYPE s=sin(base_w*a1)*r1r;
		o2.r+=c;
		o2.i+=s;
		buffer[ix+iy*OX+i*OX*OY]=o2;
		a1*=INTENSITYW;
		r1r*=INTENSITYW;
	}
}




__kernel void AddLight(__global Complex *buffer,__global TYPE *buffer2,__global TYPE *colFuncBuf)
{
	uint id = get_global_id(0);
	uint ix = id%OX;
	uint iy = id/OX;
	TYPE smr=0;
	TYPE smg=0;
	TYPE smb=0;
	TYPE r,g,b;
	TYPE col;
	for(uint i=0;i<SPLIT_N;i++)
	{
		r=colFuncBuf[i*3+0];
		g=colFuncBuf[i*3+1];
		b=colFuncBuf[i*3+2];
		Complex o2=buffer[id+i*OX*OY];
		col=(o2.r*o2.r+o2.i*o2.i);//sqrt
		smr+=col*r;
		smg+=col*g;
		smb+=col*b;
	}
	
	buffer2[(id)*3+0]=smr;
	buffer2[(id)*3+1]=smg;
	buffer2[(id)*3+2]=smb;
}





__kernel void SumReduction(__global TYPE *buffer,__global TYPE *buffer2,__local TYPE *block)
{
	uint idx = get_global_id(0);
	uint lid = get_local_id(0);
	TYPE totalval = 0.0;
	for(uint i=lid;i<OX*OY*3;i+=1024)
	{
		totalval+=buffer[i];
	}
	block[lid]=totalval;
	
	for(uint i=512;i>0;i/=2)
	{
		barrier(CLK_LOCAL_MEM_FENCE);
		if (idx<i){
			block[idx]+=block[idx+i];
		}
	}
	
	if (idx==0){
		buffer2[0]=block[0];
	}
}


