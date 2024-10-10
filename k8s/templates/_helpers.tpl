{{/*
Generate a fullname for resources based on the release name and the chart name.
*/}}
{{- define "aria-agents.fullname" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end }}