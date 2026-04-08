// Step1 helper routines:
// - command line parsing
// - input path resolution
// - run name generation
// - spectrum preset selection
// - lint generation

goto *step1_params_and_spectrum_end

*parseCommandLine
	token=""
	inQuote=0
	cmdline_work=""
	cmdline_work=cmdline_raw
	cmdline_len=strlen(cmdline_work)
	if cmdline_len<=0 : return
	repeat cmdline_len
		ch=peek(cmdline_raw,cnt)
		if ch=34 {
			inQuote=1-inQuote
			continue
		}
		if (ch=32)&(inQuote=0) {
			if strlen(token)>0 {
				argToken=token
				gosub *applyArgToken
				token=""
			}
			continue
		}
		token+=strmid(cmdline_raw,cnt,1)
	loop
	if strlen(token)>0 {
		argToken=token
		gosub *applyArgToken
	}
	return

*applyArgToken
	eqPos=instr(argToken,0,"=")
	if eqPos<0 {
		if (argToken="help")|(argToken="-h")|(argToken="/?") : gosub *showUsage
		return
	}
	argKey=strmid(argToken,0,eqPos)
	argValue=strmid(argToken,eqPos+1,strlen(argToken)-eqPos-1)
	if argKey="input" : input_path=argValue : return
	if argKey="distance" : distance=double(argValue) : return
	if argKey="gxy" : g_xyScale=double(argValue) : return
	if argKey="z0" : z0xyScale=double(argValue) : return
	if argKey="ox" : OX=int(argValue) : return
	if argKey="oy" : OY=int(argValue) : return
	if argKey="splitn" : split_n=int(argValue) : return
	if argKey="spec" : spec_name=argValue : spec_mode=0 : return
	if argKey="specvals" : spec_values_raw=argValue : spec_mode=1 : return
	if argKey="specfile" : spec_file_path=argValue : spec_mode=2 : return
	if argKey="tag" : run_tag=argValue : return
	return

*showUsage
	dialog "usage: Step1_StarBurst.exe input=mask.png distance=0.000001 gxy=0.00000002 z0=0.000005 ox=4096 oy=4096 splitn=30 spec=white tag=test"
	end

*resolveInputPath
	if strlen(input_path)>=2 {
		if strmid(input_path,1,1)=":" : return
	}
	if strmid(input_path,0,1)="\\" : return
	input_path=dir_exe+"\\"+input_path
	return

*resolveSpecFilePath
	if spec_mode!=2 : return
	if strlen(spec_file_path)>=2 {
		if strmid(spec_file_path,1,1)=":" : return
	}
	if strmid(spec_file_path,0,1)="\\" : return
	spec_file_path=dir_exe+"\\"+spec_file_path
	return

*buildRunStem
	if run_tag!="" {
		runStem=run_tag
		return
	}
	baseName=getpath(input_path,1+8+16)
	runStem=baseName
	if spec_mode=0 {
		runStem+="_s"+spec_name
	}
	if spec_mode=1 {
		runStem+="_svals"
	}
	if spec_mode=2 {
		runStem+="_sf_"+getpath(spec_file_path,1+8+16)
	}
	runStem+="_ox"+OX
	runStem+="_oy"+OY
	runStem+="_n"+split_n
	runStem+="_d"+strf("%d",distance*100000000.0)
	runStem+="_g"+strf("%d",g_xyScale*100000000000.0)
	runStem+="_z"+strf("%d",z0xyScale*100000000.0)
	return

*validateRuntimeParams
	if OX<=0 : dialog "ox must be > 0" : end
	if OY<=0 : dialog "oy must be > 0" : end
	if split_n<=0 : dialog "splitn must be > 0" : end
	return

*initSpectrumWaves
	ddim specWave,SPEC_POINT_N
	specWave.0=390.0,430.0,470.0,510.0,550.0,590.0,630.0,670.0,710.0,800.0
	return

*setSpectrumPreset
	// future extension point for external spectral databases
	ddim specAnchor,SPEC_POINT_N
	if spec_name="white" {
		specAnchor.0=1.00,1.00,1.00,1.00,1.00,1.00,1.00,1.00,1.00,1.00
		return
	}
	if spec_name="warm" {
		specAnchor.0=0.25,0.30,0.45,0.70,0.95,1.10,1.22,1.30,1.28,1.18
		return
	}
	if spec_name="cool" {
		specAnchor.0=1.20,1.18,1.12,1.00,0.88,0.74,0.62,0.54,0.48,0.40
		return
	}
	if spec_name="daylight" {
		specAnchor.0=0.92,1.02,1.10,1.08,1.00,0.96,0.94,0.92,0.90,0.86
		return
	}
	if spec_name="tungsten" {
		specAnchor.0=0.08,0.10,0.15,0.24,0.45,0.78,1.10,1.32,1.45,1.55
		return
	}
	if spec_name="candle" {
		specAnchor.0=0.02,0.03,0.05,0.09,0.18,0.44,0.92,1.42,1.72,1.95
		return
	}
	if spec_name="sunset" {
		specAnchor.0=0.08,0.12,0.20,0.33,0.52,0.85,1.18,1.42,1.34,1.08
		return
	}
	if spec_name="amber" {
		specAnchor.0=0.02,0.04,0.08,0.18,0.46,1.00,1.34,1.12,0.66,0.26
		return
	}
	if spec_name="teal" {
		specAnchor.0=0.22,0.56,1.08,1.24,1.02,0.58,0.26,0.12,0.08,0.06
		return
	}
	if spec_name="cyan" {
		specAnchor.0=0.36,0.84,1.28,1.18,0.72,0.26,0.10,0.06,0.05,0.04
		return
	}
	if spec_name="green" {
		specAnchor.0=0.03,0.08,0.20,0.86,1.30,0.82,0.18,0.06,0.03,0.02
		return
	}
	if spec_name="blue_soft" {
		specAnchor.0=0.82,1.12,1.20,0.82,0.34,0.12,0.06,0.04,0.03,0.02
		return
	}
	if spec_name="blue_hard" {
		specAnchor.0=0.48,1.28,1.36,0.32,0.06,0.02,0.01,0.01,0.01,0.01
		return
	}
	if spec_name="purple" {
		specAnchor.0=0.96,0.74,0.42,0.16,0.12,0.20,0.44,0.90,1.06,0.78
		return
	}
	if spec_name="extreme_red" {
		specAnchor.0=0.00,0.00,0.00,0.00,0.00,0.02,0.12,0.48,0.98,1.22
		return
	}
	if spec_name="extreme_yellow" {
		specAnchor.0=0.00,0.00,0.02,0.14,0.76,1.24,0.40,0.03,0.00,0.00
		return
	}
	if spec_name="extreme_green" {
		specAnchor.0=0.00,0.01,0.06,0.52,1.24,0.28,0.02,0.00,0.00,0.00
		return
	}
	if spec_name="extreme_cyan" {
		specAnchor.0=0.02,0.26,1.08,1.20,0.30,0.02,0.00,0.00,0.00,0.00
		return
	}
	if spec_name="extreme_blue" {
		specAnchor.0=0.84,1.24,0.30,0.02,0.00,0.00,0.00,0.00,0.00,0.00
		return
	}
	if spec_name="extreme_violet" {
		specAnchor.0=1.26,0.54,0.06,0.00,0.00,0.00,0.00,0.00,0.16,0.62
		return
	}
	dialog "unknown spec ["+spec_name+"]"
	end

*buildSpectrumWeights
	if spec_mode=1 : gosub *buildSpectrumWeightsFromValues : return
	if spec_mode=2 : gosub *buildSpectrumWeightsFromFile : return
	gosub *buildSpectrumWeightsFromPreset
	return

*buildSpectrumWeightsFromPreset
	ddim lint,split_n
	lm_=787.0
	repeat split_n
		sample_wave=lm_
		gosub *sampleSpectrum
		lint.cnt=sample_value
		lm_/=splitIntensity
	loop
	return

*buildSpectrumWeightsFromValues
	split spec_values_raw, ",", specValueTmp
	if stat!=split_n {
		dialog "specvals count must match splitn"
		end
	}
	ddim lint,split_n
	repeat split_n
		lint.cnt=double(specValueTmp(cnt))
	loop
	return

*buildSpectrumWeightsFromFile
	gosub *resolveSpecFilePath
	specFileBuf=""
	notesel specFileBuf
	noteload spec_file_path
	ddim fileWave,notemax
	ddim fileValue,notemax
	fileCount=0
	repeat notemax
		noteget line,cnt
		if line="" : continue
		if strmid(line,0,1)="#" : continue
		split line, ",", pair
		if stat<2 : continue
		fileWave.fileCount=double(pair(0))
		fileValue.fileCount=double(pair(1))
		fileCount++
	loop
	noteunsel
	if fileCount<2 {
		dialog "specfile needs at least 2 csv rows: wavelength,intensity"
		end
	}
	ddim lint,split_n
	lm_=787.0
	repeat split_n
		sample_wave=lm_
		gosub *sampleSpectrumFile
		lint.cnt=sample_value
		lm_/=splitIntensity
	loop
	return

*sampleSpectrum
	if sample_wave<=specWave.0 {
		sample_value=specAnchor.0
		return
	}
	repeat SPEC_POINT_N-1
		i=cnt
		w0=specWave.i
		w1=specWave.(i+1)
		if sample_wave<=w1 {
			t=(sample_wave-w0)/(w1-w0)
			sample_value=specAnchor.i*(1.0-t)+specAnchor.(i+1)*t
			return
		}
	loop
	sample_value=specAnchor.(SPEC_POINT_N-1)
	return

*sampleSpectrumFile
	if sample_wave<=fileWave.0 {
		sample_value=fileValue.0
		return
	}
	repeat fileCount-1
		i=cnt
		w0=fileWave.i
		w1=fileWave.(i+1)
		if sample_wave<=w1 {
			t=(sample_wave-w0)/(w1-w0)
			sample_value=fileValue.i*(1.0-t)+fileValue.(i+1)*t
			return
		}
	loop
	sample_value=fileValue.(fileCount-1)
	return

*step1_params_and_spectrum_end
