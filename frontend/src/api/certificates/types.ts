export interface Certificate {
    uuid: string;
    registration: string; // uuid
    file: string; // url
    issued_at: string;
    certificate_code: string;
}

export interface CertificateTemplate {
    uuid: string;
    name: string;
    file: string; // html/image
    is_default: boolean;
}
